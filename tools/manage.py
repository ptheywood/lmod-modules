#!/usr/bin/env python3

"""
Python script to link / copy module files from the available pool area into deployed directory. 
Ideally this should check that they should be available.

@todo - support deploying / withdrawing module trees - i.e dev/gcc to deploy all gcc moduels
@todo - add module deployment dependency support. I.e. dev/gcc-7 can only be deployed if the relevant binary files exist. This will require reading into the module files to be automatic, otherwise explicit rules might need adding, which duplicate some of the modulefile contents. --auto would also remove broken modules.
"""

import argparse
import pathlib
import os

PYMODULE_DIR = pathlib.Path(__file__).parent

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
        available = ModulefileDirectory(self.AVAILABLE_MODULES_DIR)
        return available

    def find_deployed(self):
        deployed = ModulefileDirectory(self.DEPLOYED_MODULES_DIR)
        return deployed

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
        if path == self.DEPLOYED_MODULES_DIR.resolve():
            return

        # If the path is in the deployment folder.
        if self.DEPLOYED_MODULES_DIR in path.parents:
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

    def clean(self):
        # Withdraw all modules
        self.find_deployed()
        count = 0
        for modulename in self.deployed.modulefiles():
            self.withdraw(modulename)
            count += 1

        if self.verbose:
            print(f"{count} modules were withdrawn")


    def install(self):
        # @todo guard to only add to path if that dir exits, incase these files are moved.
        s = f"If using LMOD, modify .bashrc to include:\n\n"
        s += f"export MODULEPATH=\"{self.DEPLOYED_MODULES_DIR}:$MODULEPATH\"\n"
        
        print(s)

    def autoupdate(self):
        print("@todo - autodeployment based on dependencies.")
        modulefiles = self.not_deployed_modulefiles()

        for modulename in sorted(modulefiles):
            self.deploy(modulename)

    def cli(self, args):
        # Process cli arguments, performing the appropriate action.
        if args.list or args.list_available:
            self.list_available()
        if args.list or args.list_deployed:
            self.list_deployed()
        if args.install:
            self.install()
        if args.auto:
            self.autoupdate()
        
        if args.clean:
            self.clean()

        if args.deploy is not None and len(args.deploy):
            for modulename in args.deploy:
                self.deploy(modulename)


        if args.withdraw is not None and len(args.withdraw):
            for modulename in args.withdraw:
                self.withdraw(modulename)
        
        # Finally provide a summary of the new state
        if args.summary:
            self.summary()

def parse_cli():
    parser = argparse.ArgumentParser(
        description="Manage module files available on the system"
        )

    # @todo add options for cli useage for comman use.

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
        "--clean",
        action="store_true",
        help="Withdraw all modules."
    )

    parser.add_argument(
        "--auto",
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
