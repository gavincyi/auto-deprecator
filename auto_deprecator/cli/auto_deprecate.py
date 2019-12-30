import ast

import click

from auto_deprecator.deprecate import check_deprecation


def check_import_deprecator_exists(tree, final_lineno):
    import_deprecator_lines = []

    for index, body in enumerate(tree.body):
        if (isinstance(body, (ast.ImportFrom, ast.Import)) and
                body.module == 'auto_deprecator'):
            start_lineno = body.lineno

            if index != len(tree.body) - 1:
                end_lineno = tree.body[index + 1].lineno
            else:
                end_lineno = final_lineno

            import_deprecator_lines.append((start_lineno, end_lineno))

    return import_deprecator_lines


def check_body_deprecator_exists(body):
    if not hasattr(body, 'decorator_list'):
        return None

    deprecate_list = [d for d in body.decorator_list
                      if d.func.id == 'deprecate']

    if len(deprecate_list) == 0:
        return None

    assert len(deprecate_list) == 1, (
        'More than one deprecate decorator is found '
        'in the function "{func}"'.format(
            func=func.name))

    return {
        kw.arg: kw.value.s
        for kw in deprecate_list[0].keywords
    }


def find_deprecated_lines(tree, curr_version, final_lineno):
    deprecated_lines = []
    deprecated_body = []

    for index, body in enumerate(tree.body):
        deprecator_args = check_body_deprecator_exists(body)

        if deprecator_args is None:
            continue

        is_deprecated = check_deprecation(
            curr_version=curr_version,
            **deprecator_args)

        if not is_deprecated:
            continue

        start_lineno = body.lineno

        if index != len(tree.body) - 1:
            end_lineno = tree.body[index + 1].lineno
        else:
            end_lineno = final_lineno

        deprecated_lines.append((start_lineno, end_lineno))
        deprecated_body.append(body)

    # Remove the deprecated body from the tree
    for body in deprecated_body:
        tree.body.remove(body)

    return deprecated_lines


def deprecate_single_file(filename, curr_version=None):
    # Read file stream
    filestream = open(filename, 'r').readlines()
    tree = ast.parse(''.join(filestream))

    # Check whether deprecate is included
    deprecator_import_lines = check_import_deprecator_exists(
        tree, len(filestream) + 1)

    if not deprecator_import_lines:
        return False

    # Store the deprecated funcion line numbers. The tuple
    # is combined by the start and end line index
    deprecated_lines = find_deprecated_lines(
        tree, curr_version, len(filestream) + 1)

    if not deprecated_lines:
        return False

    # Remove the import of the auto_deprecator if no more
    # deprecate decorator is found
    if not find_deprecated_lines(tree, curr_version, len(filestream) + 1):
        deprecated_lines += deprecator_import_lines

    # Remove the deprecated functions from backward
    deprecated_lines = sorted(
        deprecated_lines,
        key=lambda x: x[0],
        reverse=True)

    for start_lineno, end_lineno in deprecated_lines:
        filestream = filestream[:start_lineno-1] + filestream[end_lineno-1:]

    # Remove the redundant newline
    filestream = ''.join(filestream).rstrip()

    # Write back the file
    open(filename, 'w+').write(filestream)

    return True


@click.command()
@click.option(
    '--filename',
    default=None,
    help='Python file name which includes the deprecated functions')
@click.option(
    '--curr-version',
    default=None,
    help='Current file or package version. If not provided, the '
         'current versions is derived from the package.')
def main(filename, curr_version):
    if filename is not None:
        deprecate_single_file(filename, curr_version)