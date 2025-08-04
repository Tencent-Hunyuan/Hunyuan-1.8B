MODEL_PATH=${MODEL_PATH}

# export VLLM_LOGGING_LEVEL=DEBUG
export VLLM_HOST_IP=$LOCAL_IP

python3 -m vllm.entrypoints.openai.api_server \
    --host ${LOCAL_IP} \
    --port 8020 \
    --trust-remote-code \
    --model ${MODEL_PATH} \
    --gpu_memory_utilization 0.92 \
    --tensor-parallel-size 2 \
    --dtype bfloat16 \
    --disable-log-stats \
    2>&1 | tee log_server.txt
