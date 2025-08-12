#!/usr/bin/bash
SCREEN_NAME="TEST-25565"
screen -p 0 -S ${SCREEN_NAME} -X eval 'stuff "say サーバー停止まで残り5秒・・・ \015"'
sleep 1s
screen -p 0 -S ${SCREEN_NAME} -X eval 'stuff "say サーバー停止まで残り4秒・・・ \015"'
sleep 1s
screen -p 0 -S ${SCREEN_NAME} -X eval 'stuff "say サーバー停止まで残り3秒・・・ \015"'
sleep 1s
screen -p 0 -S ${SCREEN_NAME} -X eval 'stuff "say サーバー停止まで残り2秒・・・ \015"'
sleep 1s
screen -p 0 -S ${SCREEN_NAME} -X eval 'stuff "say サーバー停止まで残り1秒・・・ \015"'
sleep 1s
screen -p 0 -S ${SCREEN_NAME} -X eval 'stuff "kick @a Waiting for restart :)\015"'
sleep 1s
screen -p 0 -S ${SCREEN_NAME} -X eval 'stuff "stop \015"'
sleep 5s
