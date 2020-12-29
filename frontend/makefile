
all:	vue.config.js dev deploy

# ------------------------------------------------
ifeq ($(shell hostname),ASDI-DB)

vue.config.js:
	@cp cssi.config.js vue.config.js
	echo "asdi config"

deploy:
	echo "no need for separate deploy step on asdi-db"

endif

# ------------------------------------------------
ifeq ($(shell hostname),acy_test_app_vm_rserver)

vue.config.js:
	@cp faa.config.js vue.config.js
	echo "faa config"

deploy:
	echo "not here; cd ../rs_deploy and ./deploy_me.sh"

endif

# ------------------------------------------------

prod: vue.config.js
	npm run-script build

dev: vue.config.js
	npm run-script mydev

#clean:
#	-rm    rs_deploy/templates/index.html 
#	-rm -r rs_deploy/static/*

reallyclean: # clean
	-rm vue.config.js
	-rm -r node_modules/*
	-rm -r node_modules/.bin
	-rm -r node_modules/.cache

