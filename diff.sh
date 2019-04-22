#!/bin/bash

CONTAINER_CSV_PATH="/app/urls.csv"
CONTAINER_OUTPUT_PATH="/app/output"

while :
do
  read -e -p "Path of CSV file: " INPUT_CSV_PATH
  if [[ "${INPUT_CSV_PATH}" == "" ]];then
    continue
  else
    break
  fi
done

while :
do
  read -e -p "Path for the output: " INPUT_OUTPUT_PATH
  if [[ "${INPUT_OUTPUT_PATH}" == "" ]];then
    continue
  else
    break
  fi
done

while :
do
  read -e -p "Number of multithreading: (1) " INPUT_THREADS
  expr "${INPUT_THREADS}" + 1 >/dev/null 2>&1
  if [[ $? -lt 2 ]];then
    break
  elif [[ "${INPUT_THREADS}" == "" ]];then
    INPUT_THREADS=1
    break
  else
    echo "Please enter a integer number."
    continue
  fi
done

while :
do
  read -e -p "Waiting time to request page (ms): (1000) " INPUT_SLEEP
  expr "${INPUT_SLEEP}" + 1 >/dev/null 2>&1
  if [[ $? -lt 2 ]];then
    break
  elif [[ "${INPUT_SLEEP}" == "" ]];then
    INPUT_SLEEP=1000
    break
  else
    echo "Please enter a integer number."
    continue
  fi
done

ABS_INPUT_CSV_PATH=$(cd $(dirname ${INPUT_CSV_PATH}) && pwd)/$(basename ${INPUT_CSV_PATH})
ABS_INPUT_OUTPUT_PATH=$(cd $(dirname ${INPUT_OUTPUT_PATH}) && pwd)/$(basename ${INPUT_OUTPUT_PATH})
echo "CSV file       : ${ABS_INPUT_CSV_PATH}"
echo "output         : ${ABS_INPUT_OUTPUT_PATH}"
echo "Threads        : ${INPUT_THREADS}"
echo "Wait time(ms)  : ${INPUT_SLEEP}"
while :
do
  read -p "Are you sure you want to continue? [y/N] " flag
  if [[ "${flag}" == "y" ]];then
    break
  elif [[ "${flag}" == "N" ]];then
    exit 0
  else
    continue
  fi
done

docker run --rm -i \
    -v ${ABS_INPUT_CSV_PATH}:${CONTAINER_CSV_PATH} \
    -v ${ABS_INPUT_OUTPUT_PATH}:${CONTAINER_OUTPUT_PATH} \
    -e CSV_PATH=${CONTAINER_CSV_PATH} \
    -e OUTPUT_PATH=${CONTAINER_OUTPUT_PATH} \
    -e THREADS_NUMBER=${INPUT_THREADS} \
    -e WAITING_TIME=${INPUT_SLEEP} \
    zenpachi/extract-html-differences

exit 0
