
def cython_files():
    import os,glob
    try:
        from Cython.Build import cythonize
        USE_CYTHON = True
    except ImportError:
        USE_CYTHON = False

    package_dir = os.path.dirname(os.path.realpath(__file__))
    cython_src = glob.glob(os.path.join(package_dir,"*.pyx"))
    include_dirs = os.path.join(package_dir,"source")
    if USE_CYTHON:
        cythonize(cython_src,language="c++",include_path=[include_dirs])

def configuration(parent_package='', top_path=None):
    from numpy.distutils.misc_util import Configuration
    import os,numpy,sys
    config = Configuration('operators', parent_package, top_path)

    extra_compile_args = []
    extra_link_args = []
    if sys.platform == "win32":
        extra_compile_args=["/openmp"]
        extra_link_args=["/openmp"]
    elif sys.platform == "darwin":
        extra_compile_args = ["-std=c++11","-fopenmp"]
        extra_link_args = ["-fopenmp"]
    else:
        # extra_compile_args = []
        # extra_link_args = []
        extra_compile_args = ["-fopenmp"]
        extra_link_args = ["-lgomp"]

    package_dir = os.path.dirname(os.path.realpath(__file__))
    include_dirs = [numpy.get_include()]
    include_dirs.append(os.path.join(package_dir,"_oputils"))
    include_dirs.append(os.path.join(package_dir,"..","tools","expm_multiply_parallel_core","source"))


    src = os.path.join(package_dir,"_oputils.cpp") 
    config.add_extension('_oputils',sources=src,include_dirs=include_dirs,
                            extra_compile_args=extra_compile_args,
                            extra_link_args=extra_link_args,
                            language="c++")

    return config

if __name__ == '__main__':
        from numpy.distutils.core import setup
        import sys
        try:
            instr = sys.argv[1]
            if instr == "build_templates":
                cython_files()
            else:
                setup(**configuration(top_path='').todict())
        except IndexError: pass
