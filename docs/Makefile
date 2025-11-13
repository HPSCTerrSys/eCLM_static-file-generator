BUILD_DIR = ./_build
SRC_DIR = ../src

docs:
	jupyter-book build -W -n --keep-going .

all: docs

.PHONY: clean

clean:
	jupyter-book clean .
