REPO=clarkadamp/brewblox-sharemycook
TAG=latest

export DOCKER_CLI_EXPERIMENTAL=enabled

# Will build your Python package, and copy the results to the docker/ directory
bash docker/before_build.sh

# Build the image for amd and arm
# Give the image a tag
# Push the image to the docker registry
docker buildx build \
    --push \
    --platform linux/amd64,linux/arm/v7 \
    --tag $REPO:$TAG \
    docker
