from conans import AutoToolsBuildEnvironment, ConanFile, tools
import platform
import os

class FreeImageConan(ConanFile):
    name = 'freeimage'

    source_version = '3.17.0'
    package_version = '2'
    version = '%s-%s' % (source_version, package_version)

    requires = 'llvm/3.3-1@vuo/stable'
    settings = 'os', 'compiler', 'build_type', 'arch'
    url = 'http://freeimage.sourceforge.net/'
    license = 'http://freeimage.sourceforge.net/license.html'
    description = 'A library to read and write many image formats'
    source_dir = 'FreeImage'
    exports_sources = '*.patch'

    def imports(self):
        self.copy('*', '%s/bin' % self.source_dir, 'bin')
        self.copy('*', '%s/lib' % self.source_dir, 'lib')

    def source(self):
        tools.get('http://downloads.sourceforge.net/freeimage/FreeImage3170.zip',
                  sha256='fbfc65e39b3d4e2cb108c4ffa8c41fd02c07d4d436c594fff8dab1a6d5297f89')
        tools.patch(patch_file='makefile.patch', base_path=self.source_dir)

        self.run('rm -Rf %s/Source/LibJPEG' % self.source_dir)
        tools.get('http://downloads.sourceforge.net/project/libjpeg-turbo/1.4.2/libjpeg-turbo-1.4.2.tar.gz',
                  sha256='521bb5d3043e7ac063ce3026d9a59cc2ab2e9636c655a2515af5f4706122233e')
        self.run('mv libjpeg-turbo-1.4.2 %s/Source/LibJPEG' % self.source_dir)

        with tools.chdir(self.source_dir):
            self.run('bash gensrclist.sh')

    def build(self):
        with tools.chdir('%s/Source/LibJPEG' % self.source_dir):
            autotools = AutoToolsBuildEnvironment(self)

            # The LLVM/Clang libs get automatically added by the `requires` line,
            # but this package doesn't need to link with them.
            autotools.libs = []

            autotools.flags.append('-Oz')

            if platform.system() == 'Darwin':
                autotools.flags.append('-mmacosx-version-min=10.10')

            env_vars = {
                'CC' : self.deps_cpp_info['llvm'].rootpath + '/bin/clang',
                'CXX': self.deps_cpp_info['llvm'].rootpath + '/bin/clang++',
                'NASM': '/usr/local/bin/yasm',
            }
            with tools.environment_append(env_vars):
                autotools.configure(build=False,
                                    host=False,
                                    args=['--quiet',
                                          '--disable-shared',
                                          '--prefix=%s' % os.getcwd()])
                autotools.make(args=['--quiet'])

        with tools.chdir(self.source_dir):
            self.run('make -j9')
            self.run('mv libfreeimage-%s.dylib-x86_64 libfreeimage.dylib' % self.source_version)
            self.run('install_name_tool -id @rpath/libfreeimage.dylib libfreeimage.dylib')

    def package(self):
        self.copy('FreeImage.h', src='%s/Source' % self.source_dir, dst='include')
        self.copy('*.dylib', src=self.source_dir, dst='lib')

    def package_info(self):
        self.cpp_info.libs = ['freeimage']
