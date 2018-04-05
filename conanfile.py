from conans import AutoToolsBuildEnvironment, ConanFile, tools
import platform
import os

class FreeImageConan(ConanFile):
    name = 'freeimage'

    source_version = '3.17.0'
    package_version = '3'
    version = '%s-%s' % (source_version, package_version)

    build_requires = 'llvm/3.3-5@vuo/stable', \
               'vuoutils/1.0@vuo/stable'
    settings = 'os', 'compiler', 'build_type', 'arch'
    url = 'http://freeimage.sourceforge.net/'
    license = 'http://freeimage.sourceforge.net/license.html'
    description = 'A library to read and write many image formats'
    source_dir = 'FreeImage'
    exports_sources = '*.patch'
    libs = {
        'freeimage': 3,
    }

    def requirements(self):
        if platform.system() == 'Linux':
            self.requires('patchelf/0.10pre-1@vuo/stable')
        elif platform.system() != 'Darwin':
            raise Exception('Unknown platform "%s"' % platform.system())

    def source(self):
        tools.get('http://downloads.sourceforge.net/freeimage/FreeImage3170.zip',
                  sha256='fbfc65e39b3d4e2cb108c4ffa8c41fd02c07d4d436c594fff8dab1a6d5297f89')
        tools.patch(patch_file='makefile.patch', base_path=self.source_dir)

        # For now, disable libjpeg-turbo on Linux since it fails with 'undefined symbol: jpeg_resync_to_restart'.
        if platform.system() == 'Darwin':
            self.run('rm -Rf %s/Source/LibJPEG' % self.source_dir)
            tools.get('http://downloads.sourceforge.net/project/libjpeg-turbo/1.4.2/libjpeg-turbo-1.4.2.tar.gz',
                      sha256='521bb5d3043e7ac063ce3026d9a59cc2ab2e9636c655a2515af5f4706122233e')
            self.run('mv libjpeg-turbo-1.4.2 %s/Source/LibJPEG' % self.source_dir)

        with tools.chdir(self.source_dir):
            self.run('bash gensrclist.sh')

        self.run('mv %s/license-fi.txt %s/%s.txt' % (self.source_dir, self.source_dir, self.name))
        if platform.system() == 'Darwin':
            self.run('mv %s/Source/LibJPEG/LICENSE.txt %s/libjpeg-turbo.txt' % (self.source_dir, self.source_dir))

    def build(self):
        import VuoUtils

        if platform.system() == 'Darwin':
            yasm = '/usr/local/bin/yasm'
        elif platform.system() == 'Linux':
            yasm = '/usr/bin/yasm'

        env_vars = {
            'CC' : self.deps_cpp_info['llvm'].rootpath + '/bin/clang',
            'CXX': self.deps_cpp_info['llvm'].rootpath + '/bin/clang++',
            'NASM': yasm,
        }

        if platform.system() == 'Darwin':
            with tools.chdir('%s/Source/LibJPEG' % self.source_dir):
                autotools = AutoToolsBuildEnvironment(self)

                # The LLVM/Clang libs get automatically added by the `requires` line,
                # but this package doesn't need to link with them.
                autotools.libs = []

                autotools.flags.append('-Oz')

                if platform.system() == 'Darwin':
                    autotools.flags.append('-mmacosx-version-min=10.10')
                elif platform.system() == 'Linux':
                    autotools.flags.append('-fPIC')

                with tools.environment_append(env_vars):
                    autotools.configure(build=False,
                                        host=False,
                                        args=['--quiet',
                                              '--disable-shared',
                                              '--prefix=%s' % os.getcwd()])
                    autotools.make(args=['--quiet'])

        with tools.chdir(self.source_dir):
            env_vars['CFLAGS'] = '-I' + ' -I'.join(self.deps_cpp_info['llvm'].include_paths)
            env_vars['LIBRARIES_X86_64'] = '-stdlib=libc++ -L%s/lib -lc++ -lc++abi' % self.deps_cpp_info['llvm'].rootpath
            self.output.info(env_vars['LIBRARIES_X86_64'])
            with tools.environment_append(env_vars):
                self.run('make -j9')

            if platform.system() == 'Darwin':
                self.run('mv libfreeimage-%s.dylib-x86_64 libfreeimage.dylib' % self.source_version)
            elif platform.system() == 'Linux':
                self.run('mv libfreeimage-%s.so libfreeimage.so' % self.source_version)

            VuoUtils.fixLibs(self.libs, self.deps_cpp_info)

    def package(self):
        if platform.system() == 'Darwin':
            libext = 'dylib'
        elif platform.system() == 'Linux':
            libext = 'so'

        self.copy('FreeImage.h', src='%s/Source' % self.source_dir, dst='include')
        self.copy('libfreeimage.%s' % libext, src=self.source_dir, dst='lib')

        self.copy('%s.txt' % self.name, src=self.source_dir, dst='license')
        self.copy('libjpeg-turbo.txt', src=self.source_dir, dst='license')

    def package_info(self):
        self.cpp_info.libs = ['freeimage']
