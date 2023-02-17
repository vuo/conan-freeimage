from conans import ConanFile, CMake, tools
import platform
import os

class FreeImageConan(ConanFile):
    name = 'freeimage'

    freeimage_version = '3.19.0'
    libjpegturbo_version = '2.1.5.1'
    package_version = '0'
    version = '%s-%s' % (freeimage_version, package_version)

    build_requires = (
        'llvm/5.0.2-5@vuo+conan+llvm/stable',
        'macos-sdk/11.0-0@vuo+conan+macos-sdk/stable',
    )
    settings = 'os', 'compiler', 'build_type', 'arch'
    url = 'http://freeimage.sourceforge.net/'
    license = 'http://freeimage.sourceforge.net/license.html'
    description = 'A library to read and write many image formats'
    source_dir = 'freeimage-svn'

    build_libjpegturbo_x86_dir = '_build_libjpegturbo_x86'
    build_libjpegturbo_arm_dir = '_build_libjpegturbo_arm'
    install_libjpegturbo_x86_dir = '_install_libjpegturbo_x86'
    install_libjpegturbo_arm_dir = '_install_libjpegturbo_arm'

    exports_sources = '*.patch'

    def requirements(self):
        if platform.system() == 'Linux':
            self.requires('patchelf/0.10pre-1@vuo/stable')
        elif platform.system() != 'Darwin':
            raise Exception('Unknown platform "%s"' % platform.system())

    def source(self):
        self.run('svn checkout https://svn.code.sf.net/p/freeimage/svn/FreeImage/trunk@1903 freeimage-svn')

        tools.patch(patch_file='makefile.patch', base_path=self.source_dir)
        tools.patch(patch_file='zlib.patch', base_path=self.source_dir)
        tools.patch(patch_file='jpeg.patch', base_path=self.source_dir)
        tools.replace_in_file('%s/Makefile.gnu' % self.source_dir, 'LIBRARIES = -lstdc++', 'LIBRARIES = -lc++')

        # For now, disable libjpeg-turbo on Linux since it fails with 'undefined symbol: jpeg_resync_to_restart'.
        if platform.system() == 'Darwin':
            self.run('rm -Rf %s/Source/LibJPEG' % self.source_dir)
            tools.get('http://downloads.sourceforge.net/project/libjpeg-turbo/%s/libjpeg-turbo-%s.tar.gz' % (self.libjpegturbo_version, self.libjpegturbo_version),
                      sha256='2fdc3feb6e9deb17adec9bafa3321419aa19f8f4e5dea7bf8486844ca22207bf')
            self.run('mv libjpeg-turbo-%s %s/Source/LibJPEG' % (self.libjpegturbo_version, self.source_dir))

        with tools.chdir(self.source_dir):
            self.run('bash gensrclist.sh')

        self.run('mv %s/license-fi.txt %s/%s.txt' % (self.source_dir, self.source_dir, self.name))
        if platform.system() == 'Darwin':
            self.run('cp %s/Source/LibJPEG/LICENSE.md %s/libjpeg-turbo.txt' % (self.source_dir, self.source_dir))

    def set_cmake_install_dirs(self, cmake, dir):
        cmake.definitions['CMAKE_INSTALL_PREFIX'] = dir
        cmake.definitions['CMAKE_INSTALL_BINDIR'] = dir
        cmake.definitions['CMAKE_INSTALL_DATAROOTDIR'] = dir
        cmake.definitions['CMAKE_INSTALL_DOCDIR'] = dir
        cmake.definitions['CMAKE_INSTALL_INCLUDEDIR'] = dir
        cmake.definitions['CMAKE_INSTALL_LIBDIR'] = dir
        cmake.definitions['CMAKE_INSTALL_MANDIR'] = dir

    def build(self):
        if platform.system() == 'Darwin':
            cmake = CMake(self)

            cmake.definitions['CMAKE_BUILD_TYPE'] = 'Release'
            cmake.definitions['CMAKE_C_COMPILER'] = '%s/bin/clang'   % self.deps_cpp_info['llvm'].rootpath
            cmake.definitions['CMAKE_C_FLAGS_RELEASE'] = '-Oz -DNDEBUG'
            cmake.definitions['CMAKE_INSTALL_NAME_DIR'] = '@rpath'
            cmake.definitions['CMAKE_OSX_DEPLOYMENT_TARGET'] = '10.12'
            cmake.definitions['CMAKE_OSX_SYSROOT'] = self.deps_cpp_info['macos-sdk'].rootpath
            cmake.definitions['ENABLE_SHARED'] = 'OFF'
            cmake.definitions['ENABLE_STATIC'] = 'ON'

            self.output.info("=== Build libjpeg-turbo for x86_64 ===")
            tools.mkdir(self.build_libjpegturbo_x86_dir)
            with tools.chdir(self.build_libjpegturbo_x86_dir):
                cmake.definitions['CMAKE_OSX_ARCHITECTURES'] = 'x86_64'
                cmake.definitions['CMAKE_SYSTEM_NAME'] = 'Darwin'
                cmake.definitions['CMAKE_SYSTEM_PROCESSOR'] = 'x86_64'
                self.set_cmake_install_dirs(cmake, '%s/../%s' % (os.getcwd(), self.install_libjpegturbo_x86_dir))
                cmake.configure(source_dir='../%s/Source/LibJPEG' % self.source_dir,
                                build_dir='.')
                cmake.build()
                cmake.install()

            self.output.info("=== Build libjpeg-turbo for arm64 ===")
            tools.mkdir(self.build_libjpegturbo_arm_dir)
            with tools.chdir(self.build_libjpegturbo_arm_dir):
                cmake.definitions['CMAKE_OSX_ARCHITECTURES'] = 'arm64'
                cmake.definitions['CMAKE_SYSTEM_NAME'] = 'Darwin'
                cmake.definitions['CMAKE_SYSTEM_PROCESSOR'] = 'arm64'
                self.set_cmake_install_dirs(cmake, '%s/../%s' % (os.getcwd(), self.install_libjpegturbo_arm_dir))
                cmake.configure(source_dir='../%s/Source/LibJPEG' % self.source_dir,
                                build_dir='.')
                cmake.build()
                cmake.install()

        self.output.info("=== Build freeimage for both x86_64 + arm64 ===")
        with tools.chdir(self.source_dir):
            if platform.system() == 'Darwin':
                yasm = '/usr/local/bin/yasm'
            elif platform.system() == 'Linux':
                yasm = '/usr/bin/yasm'

            env_vars = {
                'CC' : self.deps_cpp_info['llvm'].rootpath + '/bin/clang',
                'CXX': self.deps_cpp_info['llvm'].rootpath + '/bin/clang++ -stdlib=libc++',
                'NASM': yasm,
                'MACOSX_SYSROOT': self.deps_cpp_info['macos-sdk'].rootpath,
            }
            with tools.environment_append(env_vars):
                self.run('make -f Makefile.osx -j9 libfreeimage-%s.dylib' % self.freeimage_version)

            if platform.system() == 'Darwin':
                self.run('mv libfreeimage-%s.dylib libfreeimage.dylib' % self.freeimage_version)
                self.run('install_name_tool -id @rpath/libfreeimage.dylib libfreeimage.dylib')
            elif platform.system() == 'Linux':
                self.run('mv libfreeimage-%s.so libfreeimage.so' % self.freeimage_version)

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
