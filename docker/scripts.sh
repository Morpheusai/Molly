sudo docker build -t molly_backend:v0.0.1 -f docker/Dockerfile .
docker run --net host --gpus all --restart always -v /mnt/:/mnt/ --name molly_backend -itd molly_backend:v0.0.1
