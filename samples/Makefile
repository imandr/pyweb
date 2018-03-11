FILES = \
    wsgi_app.py		wsgi_session_app.py	wsgi_threaded_app.py
	
DST_DIR = $(BUILD_DIR)/samples

build: $(DST_DIR)
	cp $(FILES) $(DST_DIR)
	cd $(DST_DIR); chmod ugo+x $(FILES)
    
$(DST_DIR):
	mkdir -p $@

    
