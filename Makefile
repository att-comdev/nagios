# Copyright 2017 The Openstack-Helm Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
DOCKER_REGISTRY            ?= quay.io
IMAGE_PREFIX               ?= attcomdev
IMAGE_TAG                  ?= latest
HELM                       ?= helm
LABEL                      ?= commit-id
IMAGE_NAME                 := nagios
PROXY                  	  ?= http://proxy.foo.com:8000
NO_PROXY                   ?= localhost,127.0.0.1,.svc.cluster.local
USE_PROXY                  ?= false

IMAGE:=${DOCKER_REGISTRY}/${IMAGE_PREFIX}/$(IMAGE_NAME):${IMAGE_TAG}

.PHONY: images
#Build all images in the list
images: $(IMAGE_NAME)
#Build and run all images in list
#sudo make images IMAGE_NAME=nagios will Build and Run nagios
$(IMAGE_NAME):
	@echo
	@echo "===== Processing [$@] image ====="
	@make build_$@ IMAGE=${DOCKER_REGISTRY}/${IMAGE_PREFIX}/$@:${IMAGE_TAG} IMAGE_DIR=${PWD}
	@make run IMAGE=${DOCKER_REGISTRY}/${IMAGE_PREFIX}/$@:${IMAGE_TAG} SCRIPT=./tools/$@_image_run.sh

# Perform Linting
.PHONY: lint
lint: pep8 helm_lint build_docs

.PHONY: docs
docs: clean build_docs

.PHONY: run
run:
	$(SCRIPT) $(IMAGE)

.PHONY: build_nagios
build_nagios:
ifeq ($(USE_PROXY), true)
	docker build --network host -t $(IMAGE) --label $(LABEL) -f Dockerfile \ 
		--build-arg http_proxy=$(PROXY) \ 
		--build-arg https_proxy=$(PROXY) \ 
		--build-arg HTTP_PROXY=$(PROXY) \ 
		--build-arg HTTPS_PROXY=$(PROXY) \ 
		--build-arg no_proxy=$(NO_PROXY) \ 
		--build-arg NO_PROXY=$(NO_PROXY) .
else
	docker build --network host -t $(IMAGE) --label $(LABEL) -f Dockerfile .
endif

.PHONY: clean
clean:
	rm -rf build

.PHONY: pep8
pep8:
	tox -e pep8

.PHONY: build_docs
build_docs:
	tox -e docs
