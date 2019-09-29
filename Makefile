build:
	python3 setup.py build

clean:
	rm -r build *.egg-info
	
.venv3: requirements.txt
	[ -d $@ ] || python3 -m venv $@
	.venv3/bin/pip3 install -r $<
	touch $@
