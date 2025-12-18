
export GATEWAY_URL="https://15dce3248ee6.ngrok-free.app"

export DEVICE_STATE_DIR=./device_state_1
python3 keygen.py
python3 enroll.py $GATEWAY_URL

export DEVICE_STATE_DIR=./device_state_2  
python3 keygen.py
python3 enroll.py $GATEWAY_URL

export DEVICE_STATE_DIR=./device_state_3  
python3 keygen.py
python3 enroll.py $GATEWAY_URL


for i in 1 2 ; do
  export DEVICE_STATE_DIR=./device_state_$i
  python3 check_enrollment.py $GATEWAY_URL
done

# Authenticate all (one-time test)
for i in 1 2 ; do 
  export DEVICE_STATE_DIR=./device_state_$i
  python3 auth.py $GATEWAY_URL
done



python3 device_daemon.py $GATEWAY_URL --interval 60
