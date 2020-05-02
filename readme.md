# Tools for managing module files

Tools for generating module files for applications. 

Should probably add support for explicit module files alongside dynamically generated ones. 


`tools/manage.py` to enable / disable module files

`tools/generate.py` to generate module files and symlinks for certain applications. 

## Todo

+ Switch to classes 
+ Combine cli to be a single applicaton with better options. 
+ Support explicit and dynamic module files to be tracked by git. 
+ Add auto deployment rules
    + This would depend on being able to tell what application the module file expects to be available. I.e. `nvcc` for the `CUDA` module, and check the version is as expected.
