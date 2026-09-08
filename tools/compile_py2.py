import marshal
import sys


def compile_file(source_path, destination_path, runtime_path):
    source_file = open(source_path, "rb")
    try:
        source = source_file.read()
    finally:
        source_file.close()
    code = compile(source, runtime_path, "exec")
    destination_file = open(destination_path, "wb")
    try:
        destination_file.write("\x03\xf3\x0d\x0a")
        destination_file.write("\x00\x00\x00\x00")
        marshal.dump(code, destination_file)
    finally:
        destination_file.close()


def main():
    if len(sys.argv) != 4:
        raise SystemExit("usage: compile_py2.py SOURCE DESTINATION RUNTIME_PATH")
    compile_file(sys.argv[1], sys.argv[2], sys.argv[3])


if __name__ == "__main__":
    main()
