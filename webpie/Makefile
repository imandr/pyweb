FILES = \
	HTTPServer.py		Version.py		WSGISessionApp.py	\
	MyThread.py		WSGIApp.py		__init__.py
	
LIB_DIR = $(BUILD_DIR)/webpie

build: $(LIB_DIR)
	cp $(FILES) $(LIB_DIR)
	cp -R webob $(LIB_DIR)
    
$(LIB_DIR):
	mkdir -p $@

    
