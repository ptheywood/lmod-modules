#!/usr/bin/env python3

"""
CLI tool for managing eveything to do with this.
"""


import argparse



"""
actions which should be able to be specified by the user:

# Summarise everything
cli summary 

auto - do everything

cli auto 
cli auto --verbose


generate - generate symlinks and module files

cli generate
cli generate --verbose 
cli generate --list
cli generate --check
cli generate --clean 


manage - enable / disable available modules

cli manage --auto
cli manage --clean 
cli manage --verbose
cli manage --list
cli manage --enable x
cli manage --withdraw x


cli ls/list --available
cli ls/list --generated
cli ls/list --enabled
cli ls/list --all

cli install 

"""

def subcommand_summary(args):
    print(f"@todo - provide a summary of the state of this tool.")
    print(f"  verbose={args.verbose}")

def subcommand_list(args):
    print(f"@todo - List certain aspects of this.")
    list_all = not any([args.available, args.deployed, args.generated, args.symlinks, args.explicit])
    if args.available or list_all:
        print(f"  @todo - list available")
    if args.deployed or list_all:
        print(f"  @todo - list deployed")
    if args.generated or list_all:
        print(f"  @todo - list generated")
    if args.symlinks or list_all:
        print(f"  @todo - list symlinks")
    if args.explicit or list_all:
        print(f"  @todo - list explicit")
    print(f"  verbose={args.verbose}")

def subcommand_auto(args):
    print(f"Autogenerate and autodeply")
    if args.check:
        print("  Check auto")
    if args.reset:
        print("  Reset auto")
    print(f"  verbose={args.verbose}")

def subcommand_generate(args):
    print(f"generate: f{args}")
    if args.list_targets:
        print(f"  list_targets")
    if args.reset:
        print(f"  reset")
    print(f"  verbose={args.verbose}")

def subcommand_manage(args):
    print(f"manage: f{args}")
    if args.auto_deploy:
        print(f"  auto_deploy")
    if args.reset:
        print(f"  reset")
    if args.deploy:
        print(f"  deploy : {args.deploy} ")
    if args.withdraw:
        print(f"  withdraw : {args.withdraw} ")
    print(f"  verbose={args.verbose}")

def subcommand_install(args):
    print(f"install: f{args}")

def cli_subcommands():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(
        title='subcommand',
        # description='valid subcommands',
        # help='extra help',
        required=True,
        dest="subcommand"  # required for required subparsers. 
    )

    # --------------
    parser_summary = subparsers.add_parser(
        "summary",
        description="Summarises the state of lmod modulefiles in this directory",
        help="Summarises the state of this tool"
    )
    parser_summary.set_defaults(func=subcommand_summary)
    parser_summary.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    # --------------
    parser_list = subparsers.add_parser(
        "list",
        aliases=["ls"],
        description="List lmod modulefiles",
        help="List lmod modulefiles and symlinks"
    )
    parser_list.set_defaults(func=subcommand_list)
    parser_list.add_argument(
        "--available",
        action="store_true",
        help="List available modules"
    )
    parser_list.add_argument(
        "--deployed",
        action="store_true",
        help="List deployed submodules"
    )
    parser_list.add_argument(
        "--generated",
        action="store_true",
        help="List generated submodules"
    )
    parser_list.add_argument(
        "--symlinks",
        action="store_true",
        help="List generated symbolic links"
    )
    parser_list.add_argument(
        "--explicit",
        action="store_true",
        help="List explicit submodules"
    )
    parser_list.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    # --------------
    parser_auto = subparsers.add_parser(
        "auto",
        description="Automatic generation and deployment of module files",
        help="Automatic generation and deployment of module files"
    )
    parser_auto.set_defaults(func=subcommand_auto)
    parser_auto.add_argument(
        "--check",
        action="store_true",
        help="Check for which modules could be created"
    )
    parser_auto.add_argument(
        "--reset",
        action="store_true",
        help="Automatically reset to default state"
    )
    parser_auto.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    # --------------
    parser_generate = subparsers.add_parser(
        "generate",
        description="Generate modulefiles and symlinks",
        help="Generate modulefiles and symlinks"
    )
    parser_generate.set_defaults(func=subcommand_generate)
    parser_generate.add_argument(
        "--list-targets",
        action="store_true",
        help="List what applications will be searched for"
    )
    parser_generate.add_argument(
        "--reset",
        action="store_true",
        help="Delete generated modules and symlinks"
    )
    parser_generate.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    # --------------
    parser_manage = subparsers.add_parser(
        "manage",
        description="Manage the availability of modulefiles to lmod",
        help="Manage the availability of modulefiles to lmod"
    )
    parser_manage.set_defaults(func=subcommand_manage)
    parser_manage.add_argument(
        "--auto-deploy",
        action="store_true",
        help="automatically deploy all possible modulefiles"
    )
    parser_manage.add_argument(
        "--reset",
        action="store_true",
        help="withdraw all module files"
    )
    parser_manage.add_argument(
        "--deploy",
        type=str,
        nargs="+",
        help="deploy the specified modulefile(s)"
    )
    parser_manage.add_argument(
        "--withdraw",
        type=str,
        nargs="+",
        help="withdraw the specified modulefile(s) files"
    )
    parser_manage.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    # --------------
    parser_install = subparsers.add_parser(
        "install",
        description="Detail how this tool can be installed (.bashrc)",
        help="Detail how this tool can be installed (.bashrc)"
    )
    parser_install.set_defaults(func=subcommand_install)
    parser_install.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    # --------------

    # Parse the arguments
    args = parser.parse_args()

    # Call the associated function, with the correct arguments.
    return_code = args.func(args) 
    return return_code

def main():
    return_code = cli_subcommands()
    return return_code


if __name__ == "__main__":
    main()
