# Republish image to AWS ECR

Start this from within the app repository folder `bench_dir/apps/iq_core`

```sh
cd bench_dir/apps/iq_core
```

## From a remote image build in a package repository, indexed in delivery/docker-images.json.

```sh
# Call it for gh (github) in this case
delivery/wait_and_republish_fn.sh "gh"

# Call it for gh (github) in this case, with other target image name (iq-base, instead of iq-core)
delivery/wait_and_republish_fn.sh "gh" "iq-xy"
```

## From a local image build

```sh
# Or also use local image with "local:" prefix
# uses latest tag by default
delivery/wait_and_republish_fn.sh "local:iqf"

# use specific local tag and publish it with the same tag name
delivery/wait_and_republish_fn.sh "local:iqf:latest"

# use latest from local tag and v13.5.4 as dest tag
delivery/wait_and_republish_fn.sh "local:iqf:latest:v13.5.4"
```

