# RHEL 8.8 서버에서 인터넷 없이 NVIDIA A10 드라이버 및 Ollama Docker 설치를 진행하는 방법

### STEP-1. GPU 확인 
lspci | grep -i nvidia

### STEP-2. nvidia driver download 
Linux 64-bit RHEL 8
Data Center Driver for Linux RHEL 8
What is an NVIDIA Recommended Driver?
This driver meets the quality levels applied to Windows drivers that pass testing in Windows Hardware Quality Labs (WHQL), therefore providing the same attention to driver reliability, robustness, and performance for non-Windows operating systems (e.g., Linux).

 - Driver Version: 570.86.15
 - CUDA Toolkit: 12.8
 - Release Date: Mon Jan 27, 2025
 - File Size: 549.66 MB
 - Info:


 ### STEP-3. CUDA Toolkit Installer 다운로드 

 - wget https://developer.download.nvidia.com/compute/cuda/12.8.0/local_installers/cuda_12.8.0_570.86.10_linux.run
 - sudo sh cuda_12.8.0_570.86.10_linux.run

 ### STEP-4. nvidia driver 랑 CUDA 패키지 서버 업로드 

 ### STEP-5. nvidia driver 랑 CUDA 패키지 설치 
  
 ### STEP-6 Nouveau 기본 드라이버 비활성화
- sudo bash -c "echo 'blacklist nouveau' > /etc/modprobe.d/blacklist-nouveau.conf"
- sudo bash -c "echo 'options nouveau modeset=0' >> /etc/modprobe.d/blacklist-nouveau.conf"
- sudo dracut --force
- sudo reboot

 ### STEP-7 NVIDIA 드라이버 설치 
- sudo dnf install -y nvidia-driver-local-repo-rhel8-570.86.15-1.0-1.x86_64.rpm
- 또는 sudo rpm -ivh nvidia-driver-local-repo-rhel8-570.86.15-1.0-1.x86_64.rpm

- 관련 패키지 설치 
 - - sudo dnf install ./kernel-devel-*.rpm ./kernel-headers-*.rpm ./gcc-*.rpm ./make-*.rpm ./dkms-*.rpm ./libglvnd-*.rpm ./pkgconfig-*.rpm ./acpid-*.rpm
- 설치 검증 
 - - rpm -q kernel-devel kernel-headers gcc make dkms libglvnd libglvnd-glx libglvnd-opengl libglvnd-devel pkgconfig acpid
- sudo reboot

설치확인. 정상적인 출력이 나오면 성공적으로 설치된 것임. 
- nvidia-smi 

 ### STEP-8 CUDA 설치 
- chmod +x cuda_12.2.0_535.104.05_linux.run
- sudo ./sudo sh cuda_12.8.0_570.86.10_linux.run --silent --toolkit

환경변수 설정: 
- echo 'export PATH=/usr/local/cuda/bin:$PATH' >> ~/.bashrc
- echo 'export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
- source ~/.bashrc

설치 확인
- nvcc --version


###  Ollama 다운로드
### Ollama 압축 해제 및 설치
다운로드한 ollama-linux-amd64.tgz 파일을 RHEL 서버에서 설치
# 1. 압축 해제
tar -xvzf ollama-linux-amd64.tgz

# 2. 실행 가능한 위치로 이동
sudo mv ollama /usr/local/bin/

# 3. 실행 권한 부여
sudo chmod +x /usr/local/bin/ollama

### Ollama 실행 및 확인
- ollama --version

Ollama 실행 테스트
- ollama run mistral 

 
 
### Ollama 자동실행 
```sh
sudo tee /etc/systemd/system/ollama.service <<EOF
[Unit]
Description=Ollama AI Model Server
After=network.target

[Service]
ExecStart=/usr/local/bin/ollama serve
Restart=always
User=root

[Install]
WantedBy=multi-user.target
EOF
```

서비스 활성화 및 시작 

```sh
sudo systemctl daemon-reload
sudo systemctl enable ollama
sudo systemctl start ollama
```

서비스 상태 확인

```sh
sudo systemctl status ollama
```

 
### llm 모델 다운로드 
EEVE-Korean-Instruct-10.8B-v1.0-GGUF 


### 모델 파일을 적절한 위치에 저장
- mkdir -p ~/.ollama/models/eeve-korean
- mv EEVE-Korean-Instruct-10.8B-v1.gguf ~/.ollama/models/eeve-korean/


### ModelFile 수정 
```txt 
FROM ~/.ollama/models/eeve-korean/EEVE-Korean-Instruct-10.8B-v1.gguf

TEMPLATE """{{- if .System }}
<s>{{ .System }}</s>
{{- end }}
<s>Human:
{{ .Prompt }}</s>
<s>Assistant:
"""

SYSTEM """A chat between a curious user and an artificial intelligence assistant. The assistant gives helpful, detailed, and polite answers to the user's questions."""

PARAMETER stop <s>
PARAMETER stop </s>
```

### Ollama 모델 등록 
ollama create eeve-korean ~/.ollama/models/eeve-korean/Modelfile

### Ollama 모델 실행 
ollama run eeve-korean

 
