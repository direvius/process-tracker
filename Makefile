build:
install: process-tracker
	install -m 0755 process-tracker -t $(DESTDIR)/usr/bin
	dh_installman debian/process-tracker.1
.PHONY: install

