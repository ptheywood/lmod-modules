#!/usr/bin/env python3

import argparse
import pathlib
import os
import re
import shutil

SCRIPT_DIR = pathlib.Path(__file__).parent
SYMLINKS_DIR = pathlib.Path(SCRIPT_DIR, "..", "symlinks").resolve()
MODULEFILES_DIR = pathlib.Path(SCRIPT_DIR, "..", "available").resolve()
# MODULEFILES_DIR = pathlib.Path(SCRIPT_DIR, "..", "available").resolve()


def generate_modulefile_string(
    appname, 
    version, 
    whatis, 
    prepend_vars = [], 
    set_vars = []):


    lines = []
    # Comment at the top
    lines.append(f"# {appname} {version} module")
    # Declare the app name 
    lines.append(f"set app {appname}")
    # Declare the version
    lines.append(f"set version {version}")
    # Add the whatis string
    if whatis is not None:
        lines.append(f"module-whatis \"{whatis}\"")
    # Set the family name for conflicts.
    lines.append(f"family {appname}")

    # For each passed in path, add it.
    for vname, vval in prepend_vars:
        lines.append(f"prepend-path {vname} {vval}")

    # Set each environment variable
    for vname, vval in set_vars:
        lines.append(f"setenv {vname} {vval}")
    
    s = "\n".join(lines)
    return s



def find_versions(search_dir, pattern, optional=False):
    search_path = pathlib.Path(search_dir).expanduser()
    regex = re.compile(pattern)

    versions = {}
    for path in search_path.iterdir():
        result = regex.match(path.name)
        if result:
            # print(path, pattern, result)
            version = result.group(1)
            # print(version)
            path = path.resolve()

            versions[version] = {"path": path, "version": version}

    return versions



def find_applications(applications):
    for app, obj in applications.items():
        common_versions = None
        common_versions_optional = None
        for dependency in obj["dependencies"]:
            optional = dependency["optional"] if "optional" in dependency else False
            versions = find_versions(
                dependency["search_dir"],
                dependency["pattern"],
                optional
            )
            dependency["versions"] = versions
            versions_set = set(versions.keys())
            if not optional:
                common_versions = common_versions.intersection(versions_set) if common_versions is not None else versions_set
            else:
                common_versions_optional = common_versions_optional.intersection(versions_set) if common_versions_optional is not None else versions_set

        if common_versions is None:
            common_versions = set()
        if common_versions_optional is None:
            common_versions_optional = set()

        obj["versions"] =  common_versions.union( common_versions_optional)
        # print(sorted(list(common_versions)))
        # print(sorted(list(common_versions_optional)))
    return applications


# @todo move this/rename
def process_applications():

    # Define the apps and files they depend on. Versions of dependencies must match!
    # @todo version command to extract full version for modulefiles?
    applications = {
        "CUDA": {
            "versions": None,
            "modulefile": {
                "required": True,
                "whatis": "Adds CUDA compiler and library paths",
                "prepend-path": [
                    ("PATH", "/usr/local/cuda-{version}/bin"),
                    ("LD_LIBRARY_PATH", "/usr/local/cuda-{version}/lib:"),
                    ("LD_LIBRARY_PATH", "/usr/local/cuda-{version}/lib64:"),
                ],
                "setenv": []
            },
            "dependencies": [
                {
                    "name": "cuda",
                    "search_dir": "/usr/local",
                    "pattern": r"^cuda-([0-9]+\.[0-9]+)$",
                    "symlink_required": False,
                }
            ],
            "symlink_dirs": {}
        },
        "gcc": {
            "versions": None,
            "modulefile": {
                "required": True,
                "whatis": "Adds GCC toolchain to the path",
                "prepend-path": [
                    ("PATH", "{symlink_dir}"),
                ],
                "setenv" : [
                    ("CC", "gcc"),
                    ("CXX", "g++"),
                ]
            },
            "dependencies": [
                {
                    "name": "gcc",
                    "search_dir": "/usr/bin",
                    "pattern": r"^gcc-([0-9]+)$",
                    "symlink_required": True,
                },
                {
                    "name": "g++",
                    "search_dir": "/usr/bin",
                    "pattern": r"^g\+\+-([0-9]+)$",
                    "symlink_required": True,
                }
            ],
            "symlink_dirs": {}
        },
        "cmake": {
            "versions": None,
            "modulefile": {
                "required": True,
                "whatis": "Adds cmake to the path",
                "prepend-path": [
                    ("PATH", "~/bin/cmake/{version}-Linux-x86_64/bin"),
                    ("MANPATH", "~/bin/cmake/{version}-Linux-x86_64/man")
                ],
                "setenv" : []
            },
            "dependencies": [
                {
                    "name": "cmake",
                    "search_dir": "~/bin/cmake/",
                    "pattern" : r"^cmake-([0-9]+\.[0-9]+\.[0-9]+)-Linux-x86_64$",
                    "symlink_required": False
                }
            ],
            "symlink_dirs": {}
        }, 
        "clang": {
            "versions": None,
            "modulefile": {
                "required": True,
                "whatis": "Adds installed components of the Clang toolchain to the path",
                "prepend-path": [
                    ("PATH", "{symlink_dir}"),
                ],
                "setenv" : [
                    ("CC", "clang"),
                    ("CXX", "clang"),
                ]
            },
            "dependencies": [
                {
                    "name": "clang",
                    "search_dir": "/usr/bin",
                    "pattern": r"^clang-([0-9]+)$",
                    "symlink_required": True,
                },
                {
                    "name": "clang-tidy",
                    "search_dir": "/usr/bin",
                    "pattern": r"^clang-tidy-([0-9]+)$",
                    "symlink_required": True,
                    "optional": True,
                },
                {
                    "name": "clang-tidy",
                    "search_dir": "/usr/bin",
                    "pattern": r"^clang-tidy-([0-9]+)$",
                    "symlink_required": True,
                    "optional": True,
                },
                {
                    "name": "clang-check",
                    "search_dir": "/usr/bin",
                    "pattern": r"^clang-check-([0-9]+)$",
                    "symlink_required": True,
                    "optional": True,
                },
                {
                    "name": "clang-format",
                    "search_dir": "/usr/bin",
                    "pattern": r"^clang-format-([0-9]+)$",
                    "symlink_required": True,
                    "optional": True,
                },
                {
                    "name": "run-clang-tidy",
                    "search_dir": "/usr/bin",
                    "pattern": r"^run-clang-tidy-([0-9]+)$",
                    "symlink_required": True,
                    "optional": True,
                }
            ],
            "symlink_dirs": {}
        }
    }

    # Find applications and versions
    applications = find_applications(applications)

    # Create symlinks
    create_symlinks(applications)

    # Create module files
    create_modulefiles(applications)

# @todo - some refactoring?
def create_symlinks(applications):
    symlink_root = pathlib.Path(SYMLINKS_DIR)
    symlink_root.mkdir(exist_ok=True)
    
    created_links = []
    # Iterate found apps
    for app, obj in applications.items():
        app_dir = pathlib.Path(symlink_root, app)
        versions = obj["versions"]
        dependencies = obj["dependencies"]
        for version in versions:
            for dependency in dependencies:
                is_optional = dependency["optional"] if "optional" in dependency else False
                if dependency["symlink_required"]:
                    # If the dependency is non optional / was found for this verison

                    # Ensure the app directory exists
                    app_dir.mkdir(exist_ok=True)
                    # Ensure the application version directory exists
                    app_versions_dir = pathlib.Path(app_dir, version)
                    app_versions_dir.mkdir(exist_ok=True)

                    # Construct paths for symlink source and target
                    versions = dependency["versions"]
                    if version in versions:
                        link_source = versions[version]["path"]
                        link_target = pathlib.Path(app_versions_dir, dependency["name"])
                        obj["symlink_dirs"][version] = link_target.parent

                        # If the target does not exist, create it.
                        if not link_target.exists() and link_source.exists():
                            link_target.symlink_to(link_source)
                            created_links.append(link_target)

                    elif is_optional:
                        print(f"{app}: Optional {dependency['name']} {version} not found, continuing. ")
                    else:
                        raise Exception(f"Missing version {version} of non-optional dependency {dependency['name']} for {app}")

                        


    print_created_symlinks(created_links)
    return created_links

# @todo - don't overwrite files without a flag.
def create_modulefiles(applications):
    modulefiles_root = pathlib.Path(MODULEFILES_DIR)
    modulefiles_root.mkdir(exist_ok=True)

    created_modulefiles = []

    # Iterate applications, if they need a modulefile creating, do so. 
    # modulefiles should be created on a per-template bassis, and may need to know about symlink destinations and so on. 
    # 

    for app, obj in applications.items():
        modulefile_options = obj["modulefile"]
        if modulefile_options["required"]:
            modulefile_app_path = pathlib.Path(modulefiles_root, app)
            modulefile_app_path.mkdir(exist_ok=True)
            # Module file will be required for each version.
            versions = obj["versions"]
            for version in versions:
                modulefile_app_version_path = pathlib.Path(modulefile_app_path, version)

                # Compute the correct values of prepend_vars and set_vars.
                concrete_prepend_paths = []
                for vname, vfmt in modulefile_options["prepend-path"]:
                    format_variables = {
                        "version": version,
                        "symlink_dir": obj["symlink_dirs"][version] if "symlink_dirs" in obj and version in obj["symlink_dirs"] else ""
                    }
                    path = pathlib.Path(vfmt.format(**format_variables)).expanduser()
                    concrete_prepend_paths.append((vname, str(path)))
                concrete_setenvs = []
                for vname, vfmt in modulefile_options["setenv"]:
                    format_variables = {
                        "version": version,
                        "symlink_dir": obj["symlink_dirs"][version] if "symlink_dirs" in obj and version in obj["symlink_dirs"] else ""
                    }
                    concrete_setenvs.append((vname, vfmt.format(**format_variables)))
                whatis = modulefile_options["whatis"] if "whatis" in modulefile_options else None
                # Get the module string 
                modulestring = generate_modulefile_string(
                    appname = app,
                    version = version,
                    whatis = whatis, 
                    prepend_vars = concrete_prepend_paths,
                    set_vars = concrete_setenvs
                )

                with open(modulefile_app_version_path, "w") as fp:
                    fp.write(modulestring)
                    created_modulefiles.append(modulefile_app_version_path)

    print_created_modulefiles(created_modulefiles)
    return created_modulefiles

# @todo - method to clean only dynamically created module files

def clean_symlinks():
    symlink_root = pathlib.Path(SYMLINKS_DIR)
    if symlink_root.exists():
        shutil.rmtree(symlink_root)

def print_created_symlinks(symlinks):
    print(f"Created {len(symlinks)} symlinks")
    for x in symlinks:
        print(f"\t{x}")

def print_created_modulefiles(modulefiles):
    print(f"Created {len(modulefiles)} modulefiles")
    for x in modulefiles:
        print(f"\t{x}")

def cli():
    parser = argparse.ArgumentParser(
        description="Script to generate symlinks for module files for different versions of gcc etc."
        )

    parser.add_argument(
        "--clean",
        action="store_true",
        help="Delete the all generated symlinks."
    )

    args = parser.parse_args()
    return args

def main():
    # @todo better cli. 
    # @todo use classes?
    args = cli()

    if args.clean:
        clean_symlinks()
    else:
        process_applications()

if __name__ == "__main__":
    main()
