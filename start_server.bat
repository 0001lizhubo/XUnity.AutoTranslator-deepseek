@echo off
cd /d "%~dp0"
echo Starting llama-server with HY-MT2-7B-Q8_0...
"C:\Users\dy229\Desktop\open_4399\llama\llama-server.exe" -m "C:\Users\dy229\Desktop\open_4399\llama\HY-MT2-7B-Q8_0.gguf" -ngl 100 --temp 0.7 --top-p 0.6 --top-k 20 --repeat-penalty 1.05 -n 4096 --host 127.0.0.1 --port 8080
pause