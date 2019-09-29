.venv3: requirements.txt
	[ -d $@ ] || python3 -m venv $@
	.venv3/bin/pip3 install -r $<
	touch $@
