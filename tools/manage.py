#!/usr/bin/env python3

"""
Python script to generate module files and symlinks and manage which module files are available or in use. 

@todo - support deploying / withdrawing module trees - i.e dev/gcc to deploy all gcc moduels
@todo - add module deployment dependency support. I.e. dev/gcc-7 can only be deployed if the relevant binary files exist. This will require reading into the module files to be automatic, otherwise explicit rules might need adding, which duplicate some of the modulefile contents. --auto would also remove broken modules.
# @todo - better use of classes
# @todo - pytest
# @todo - split out applications data structure into a config file or directory of config files
"""

import argparse
import pathlib
import os
import re
import shutil

PYMODULE_DIR = pathlib.Path(__file__).parent
SYMLINKS_DIR = pathlib.Path(PYMODULE_DIR, "..", "symlinks").resolve()
MODULEFILES_DIR = pathlib.Path(PYMODULE_DIR, "..", "available").resolve()

def generate_modulefile_string(
    appname,
    family,
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
    if family is not None:
        lines.append(f"family {family}")

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
    if search_path.is_dir():
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
def generate_modules():

    # Define the apps and files they depend on. Versions of dependencies must match!
    # @todo version command to extract full version for modulefiles?
    applications = {
        "CUDA": {
            "versions": None,
            "modulefile": {
                "required": True,
                "whatis": "Adds CUDA compiler and library paths",
                "family": "CUDA",
                "prepend-path": [
                    ("PATH", "/usr/local/cuda-{version}/bin"),
                    ("LD_LIBRARY_PATH", "/usr/local/cuda-{version}/lib:"),
                    ("LD_LIBRARY_PATH", "/usr/local/cuda-{version}/lib64:"),
                ],
                "setenv": [
                    ("CUDA_PATH", "/usr/local/cuda-{version}")
                ]
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
        "nsight-systems": {
            "versions": None,
            "modulefile": {
                "required": True,
                "whatis": "Nsight Systems",
                "family": "nsys",
                "prepend-path": [
                    ("PATH", "/opt/nvidia/nsight-systems/{version}/bin"),
                ],
                "setenv": [
                ]
            },
            "dependencies": [
                {
                    "name": "nsys",
                    "search_dir": "/opt/nvidia/nsight-systems/",
                    "pattern": r"^([0-9]{4}\.[0-9]+\.[0-9]+)$",
                    "symlink_required": False,
                }
            ],
            "symlink_dirs": {}
        },
        "nsight-compute": {
            "versions": None,
            "modulefile": {
                "required": True,
                "whatis": "Nsight Compute",
                "family": "ncu",
                "prepend-path": [
                    ("PATH", "/opt/nvidia/nsight-compute/{version}"),
                ],
                "setenv": [
                ]
            },
            "dependencies": [
                {
                    "name": "ncu",
                    "search_dir": "/opt/nvidia/nsight-compute/",
                    "pattern": r"^([0-9]{4}\.[0-9]+\.[0-9]+)$",
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
                "family": "GCC",
                "prepend-path": [
                    ("PATH", "{symlink_dir}"),
                ],
                "setenv" : [
                    ("CC", "gcc"),
                    ("CXX", "g++"),
                    ("CUDAHOSTCXX", "g++")
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
                },
		{
		    "name": "gfortran",
		    "search_dir": "/usr/bin",
		    "pattern": r"^gfortran-([0-9]+)$",
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
                "family": "cmake",
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
                "family": "clang",
                "prepend-path": [
                    ("PATH", "{symlink_dir}"),
                ],
                "setenv" : [
                    ("CC", "clang"),
                    ("CXX", "clang"),
                    ("CUDAHOSTCXX", "clang"),
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
                    "name": "clang++",
                    "search_dir": "/usr/bin",
                    "pattern": r"^clang\+\+-([0-9]+)$",
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
                family = modulefile_options["family"] if "family" in modulefile_options else None
                # Get the module string 
                modulestring = generate_modulefile_string(
                    appname = app,
                    family = family,
                    version = version,
                    whatis = whatis, 
                    prepend_vars = concrete_prepend_paths,
                    set_vars = concrete_setenvs
                )
                modulefile_app_path.mkdir(exist_ok=True)
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
    for x in sorted(symlinks):
        print(f"\t{x}")

def print_created_modulefiles(modulefiles):
    print(f"Created {len(modulefiles)} modulefiles")
    for x in sorted(modulefiles):
        print(f"\t{x}")




class ModulefileDirectory:

    def __init__(self, root=None, modulefiles=None):
        self._root = root
        self._modulefiles = modulefiles if modulefiles is not None else self.load_modulefiles()
        self._itern = 0

    """
    Determine if the provided path is to an explcicit modulefile, or the parent of one or more modulepaths.
    """
    def __contains__(self, modulepath):
        path = pathlib.Path(modulepath)
        # Iterate the list of files, checking if in the parents of
        for f in self._modulefiles:
            if path == f:
                return True
            elif path in f.parents:
                return True
        # Flase if not found buy now
        return False

    def __len__(self):
        return len(self._modulefiles)

    def __iter__(self):
        self._itern = 0
        return self

    def __next__(self):
        if self._itern < len(self):
            item = self._modulefiles[self._itern]
            self._itern += 1
            return item
        else:
            raise StopIteration

    def __sub__(self, other):
        return self.difference(other)

    def __copy__(self):
        cls = self.__class__
        result = cls.__new__(cls)
        result.__dict__.update(self.__dict__)
        return result

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            setattr(result, k, deepcopy(v, memo))
        return result


    def is_file(self, modulepath):
        modulepath = pathlib.Path(modulepath)
        return modulepath in self._modulefiles

    def is_group(self, modulepath):
        modulepath = pathlib.Path(modulepath)
        for f in self.modulefiles:
            if modulepath in f.parents:
                return True
        return False

    def exists(self, modulepath):
        modulepath = pathlib.Path(modulepath)
        return self.is_file(modulepath) or self.is_group(modulepath)

    def append(self, modulefile):
        if modulefile not in self._modulefiles:
            self._modulefiles.append(modulefile)

    def remove(self, modulefile):
        if modulefile in self._modulefiles:
            self._modulefiles.remove(modulefile)

    def modulefiles(self, modulepath=None):
        if modulepath is None:
            return sorted(self._modulefiles)
        else:
            modulepath = pathlib.Path(modulepath)
            modulefiles = []
            for f in self._modulefiles:
                if modulepath == f or modulepath in f.parents:
                    modulefiles.append(f)
            return sorted(modulefiles)

    """
    Get a list of modules included not included in other.
    """
    def difference(self, other):
        assert(isinstance(other, ModulefileDirectory))

        a = set(self._modulefiles)
        b = set(other._modulefiles)

        modulefiles = list(a - b)
        return ModulefileDirectory(root=self._root, modulefiles=modulefiles)


    def load_modulefiles(self):
        modulefiles = []
        for root, dirs, files in os.walk(self._root):
            for file in files:
                absmodulepath = pathlib.Path(root, file)
                modulepath = absmodulepath.relative_to(self._root)
                modulefiles.append(modulepath)        
        return modulefiles


class ModulefileManager:
    # Paths relative to the script/modules
    SYMLINKS_DIR = pathlib.Path(PYMODULE_DIR, "..", "symlinks").resolve()
    AVAILABLE_MODULES_DIR = pathlib.Path(PYMODULE_DIR, "..", "available").resolve()
    DEPLOYED_MODULES_DIR = pathlib.Path(PYMODULE_DIR, "..", "deployed").resolve()

    def __init__(self, verbose=False):
        self.available = self.find_available()
        self.deployed = self.find_deployed()
        self.verbose = verbose

        
    def find_available(self):
        self.available = ModulefileDirectory(self.AVAILABLE_MODULES_DIR)
        return self.available

    def find_deployed(self):
        self.deployed = ModulefileDirectory(self.DEPLOYED_MODULES_DIR)
        return self.deployed

    def not_deployed_modulefiles(self):
        self.find_available()
        self.find_deployed()

        not_deployed = self.available - self.deployed
        return not_deployed.modulefiles()

    def summary(self):
        available_count = str(len(self.available))
        deployed_count = str(len(self.deployed))
        str_width = max(len(available_count), len(deployed_count))

        print(f"Modules Available: {available_count: >{str_width}}")
        print(f"Modules Deployed : {deployed_count: >{str_width}}")

    def list_available(self):
        print(f"{len(self.available)} modules available")
        for name in sorted(self.available):
            print(f"  {name}")

    def list_deployed(self):
        print(f"{len(self.deployed)} modules deployed")
        for name in sorted(self.deployed):
            print(f"  {name}")

    def modulename_from_path(self, modulepath):
        # If the path includes the available path, return the module name
        modulepath = pathlib.Path(modulepath).resolve()
        if self.AVAILABLE_MODULES_DIR in modulepath.parents:
            return modulepath.relative_to(self.AVAILABLE_MODULES_DIR)
        # elif the path includes the deployed path, return the modulename
        elif self.DEPLOYED_MODULES_DIR in modulepath.parents:
            return modulepath.relative_to(self.DEPLOYED_MODULES_DIR)
        # else raise an error.
        else:
            raise Exception(f"{modulepath} is neither available or deployed")

    def avaiable_path(self, modulename):
        return pathlib.Path(self.AVAILABLE_MODULES_DIR, modulename)

    def deployed_path(self, modulename):
        return pathlib.Path(self.DEPLOYED_MODULES_DIR, modulename)

    def is_available(self, modulename):
        modulename = pathlib.Path(modulename)
        if modulename in self.available:
            return True
        else:
            return False
    
    def is_deployed(self, modulename):
        modulename = pathlib.Path(modulename)
        if modulename in self.deployed:
            return True
        else:
            # @todo maybe exception if does not available?
            return False

    def is_deplyed_as_symlink(self, modulename):
        modulename = pathlib.Path(modulename)
        # If not deployed, return false.
        if not self.is_deployed(modulename):
            return False
        else:
            # Otherwise if the deployed modulefile is a symlink, return true.
            deployed_path = self.deployed_path(modulename)
            return deployed_path.is_symlink()

    # Exists if it's deployed or avaialbe.
    def exists(self, modulename):
        return self.is_available(modulename) or self.is_deployed(modulename)


    def deploy(self, modulepath):
        # @todo add some kind of dependency checking.
        modulepath = pathlib.Path(modulepath)
        # A module is deployed by creating a symlink in the deployed directory, if the module is not already deplyed.
        if self.is_available(modulepath):
            # Get the list of modules to acutally deploy, incase it is a group.
            modulefiles = self.available.modulefiles(modulepath)
            for modulename in modulefiles:
                if not self.is_deployed(modulename):
                    # Create the symlink.a
                    link_target = pathlib.Path(self.DEPLOYED_MODULES_DIR, modulename)
                    link_source = pathlib.Path(self.AVAILABLE_MODULES_DIR, modulename)

                    # Ensure the parent directory for the symlink.
                    deployment_directory = link_target.parent
                    deployment_directory.mkdir(parents=True, exist_ok=True)

                    link_target.symlink_to(link_source)

                    self.deployed.append(modulename)
                    if self.verbose:
                        print(f"{modulename} deployed")

        else:
            print(f"Error: Unknown modulefile {modulepath}")

    def remove_empty(self, path_in_deployed, recurse=False):
        path = pathlib.Path(path_in_deployed).resolve()
        # If th path is the deployed directory, return.
        if path == self.DEPLOYED_MODULES_DIR.resolve() or path == self.AVAILABLE_MODULES_DIR.resolve():
            return

        # If the path is in the deployment folder.
        if self.DEPLOYED_MODULES_DIR in path.parents or self.AVAILABLE_MODULES_DIR in path.parents:
            # If the path is empty
            if not any(path.parent.iterdir()):
                # Delete the directory
                path.parent.rmdir()

                # Recurse up a level.
                self.remove_empty(path.parent, recurse=True)

    def withdraw(self, modulepath):
        modulepath = pathlib.Path(modulepath)
        # Only withdraw deployed as symlink modules.
        if self.is_deployed(modulepath):
            # Get the list of modules to acutally deploy, incase it is a group.
            modulefiles = self.deployed.modulefiles(modulepath)
            for modulename in modulefiles:
                if self.is_deployed(modulename):
                    if self.is_deplyed_as_symlink(modulename):
                        deployed_path = self.deployed_path(modulename)
                        try:
                            deployed_path.unlink()

                            self.deployed.remove(modulename)
                            if self.verbose:
                                print(f"{modulename} withdrawn")

                            # If the parent directory is now empty, the directory (and subsequently empty parents) are no longer required?
                            self.remove_empty(deployed_path, recurse=True)


                        except FileNotFoundError as e:
                            print(e)
                    else:
                        raise Exception("Cannot withdraw non-symlink modulefile.")
        else:
            # @todo raise an issue.
            pass

    def withdraw_all(self):
        # Withdraw all modules
        self.find_deployed()
        count = 0
        for modulename in self.deployed.modulefiles():
            self.withdraw(modulename)
            count += 1

        if self.verbose:
            print(f"{count} modules were withdrawn")

    def delete_available(self):
        # Withdraw available modules and remove them from available.
        self.find_available()
        count = 0
        for modulename in self.available.modulefiles():
            if self.is_deployed(modulename):
                self.withdraw(modulename)

            available_path = self.avaiable_path(modulename)
            try:
                available_path.unlink()
                self.available.remove(modulename)

                # If the parent directory is now empty, the directory (and subsequently empty parents) are no longer required?
                self.remove_empty(available_path, recurse=True)
                count += 1
            except FileNotFoundError as e:
                print(e)

        if self.verbose:
            print(f"{count} modules were withdrawn")


    def install(self):
        # @todo guard to only add to path if that dir exits, incase these files are moved.
        s = f"If using LMOD, modify .bashrc to include:\n\n"
        s += f"export MODULEPATH=\"{self.DEPLOYED_MODULES_DIR}:$MODULEPATH\"\n"
        
        print(s)

    def autodeploy(self):
        print("@todo - autodeployment based on dependencies.")
        modulefiles = self.not_deployed_modulefiles()

        for modulename in sorted(modulefiles):
            self.deploy(modulename)

    def generate(self):
        generate_modules()
        # Re-find avaialable modules 
        self.find_available()

    def clean_generated(self):
        clean_symlinks()
        self.delete_available()

    def auto(self):
        self.generate()
        self.autodeploy()

    def cli(self, args):
        # Process cli arguments, performing the appropriate action.

        # Clean first if provided
        if args.clean:
            self.withdraw_all()
            self.clean_generated()

        if args.clean_deployed:
            self.withdraw_all()

        # Clean generated files
        if args.clean_generated:
            self.clean_generated()

        # Then generate if requested
        if args.generate:
            self.generate()

        # Then do managerial things
        # Generate and autodeploy
        if args.auto:
            self.auto()

        # Just autodeploy
        if args.autodeploy:
            self.autodeploy()

        if args.deploy is not None and len(args.deploy):
            for modulename in args.deploy:
                self.deploy(modulename)

        if args.withdraw is not None and len(args.withdraw):
            for modulename in args.withdraw:
                self.withdraw(modulename)
        
        # Finally list-like arguments        
        if args.install:
            self.install()

        if args.list or args.list_available:
            self.list_available()

        if args.list or args.list_deployed:
            self.list_deployed()

        # Finally provide a summary of the new state
        if args.summary:
            self.summary()

def parse_cli():
    parser = argparse.ArgumentParser(
        description="Manage module files available on the system"
        )

    parser.add_argument(
        "-s",
        "--summary",
        action="store_true",
        help="Provide a short summary of the situation."
    )

    parser.add_argument(
        "-l",
        "--list",
        action="store_true",
        help="Implies --list-available --list_deployed"
    )

    parser.add_argument(
        "--list-available",
        action="store_true",
        help="List available modules"
    )

    parser.add_argument(
        "--list-deployed",
        action="store_true",
        help="List deployed modules"
    )

    parser.add_argument(
        "--install",
        action="store_true",
        help="Describe how to install the system"
    )

    parser.add_argument(
        "--auto",
        action="store_true",
        help="Automatically generate, and deploy modules"
    )

    parser.add_argument(
        "--autodeploy",
        action="store_true",
        help="Automatically deploy and withdraw modules based on dependencies"
    )

    parser.add_argument(
        "-d",
        "--deploy",
        type=str,
        nargs="+",
        help="Modules to deploy"
    )

    parser.add_argument(
        "-w",
        "--withdraw",
        type=str,
        nargs="+",
        help="Modules to withdraw"
    )

    parser.add_argument(
        "-g",
        "--generate",
        action="store_true",
        help="Generate modules and symlinks based on avaialble applications"
    )

    parser.add_argument(
        "--clean-generated",
        action="store_true",
        help="clean generated symlinks and module files"
    )

    parser.add_argument(
        "--clean-deployed",
        action="store_true",
        help="clean deployed modules / autowithdraw all"
    )

    parser.add_argument(
        "--clean",
        action="store_true",
        help="Withdraw all modules, delete generated modules, delete symlinks"
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()
    return args

def main():
    args = parse_cli()

    # Construct the manager object
    manager = ModulefileManager(args.verbose)

    # Apply command line arguments.
    manager.cli(args)


if __name__ == "__main__":
    main()
