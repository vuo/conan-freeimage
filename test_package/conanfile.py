from conans import ConanFile
import platform

class FreeImageTestConan(ConanFile):
    generators = 'qbs'

    def build(self):
        self.run('qbs -f "%s"' % self.source_folder)

    def imports(self):
        self.copy('*', src='bin', dst='bin')
        self.copy('*', src='lib', dst='lib')

    def test(self):
        self.run('qbs run -f "%s"' % self.source_folder)

        # Ensure we only link to system libraries and our own libraries.
        if platform.system() == 'Darwin':
            self.run('! (otool -L lib/libfreeimage.dylib | grep -v "^lib/" | egrep -v "^\s*(/usr/lib/|/System/|@rpath/)")')
            self.run('! (otool -l lib/libfreeimage.dylib | grep -A2 LC_RPATH | cut -d"(" -f1 | grep "\s*path" | egrep -v "^\s*path @(executable|loader)_path")')
        elif platform.system() == 'Linux':
            self.run('! (ldd lib/libfreeimage.so | grep -v "^lib/" | grep "/" | egrep -v "(\s(/lib64/|(/usr)?/lib/x86_64-linux-gnu/)|test_package/build)")')
        else:
            raise Exception('Unknown platform "%s"' % platform.system())
