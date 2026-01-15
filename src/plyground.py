# 현재 환경 확인
import sys
import os
import platform
import subprocess

def check_environment():
    """현재 실행 환경 확인"""
    print("=" * 60)
    print("현재 실행 환경 확인")
    print("=" * 60)
    
    # 1. Python 경로 확인
    print("Python 정보:")
    print(f"  실행 경로: {sys.executable}")
    print(f"  Python 버전: {sys.version}")
    print(f"  플랫폼: {platform.platform()}")
    
    # 2. 가상환경 확인
    print(f"\n가상환경 정보:")
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print(f"  가상환경: 활성화됨")
        print(f"  가상환경 경로: {sys.prefix}")
    else:
        print(f"  가상환경: 비활성화됨")
    
    # 3. Docker 컨테이너 확인
    print(f"\nDocker 컨테이너 확인:")
    
    # /.dockerenv 파일 확인
    if os.path.exists('/.dockerenv'):
        print("  Docker 컨테이너 내부에서 실행 중")
    else:
        print("  호스트 시스템에서 실행 중")
    
    # cgroup 확인
    try:
        with open('/proc/1/cgroup', 'r') as f:
            content = f.read()
            if 'docker' in content or 'containerd' in content:
                print("  cgroup에서 Docker 확인됨")
            else:
                print("  cgroup에서 Docker 확인 안됨")
    except:
        print("  cgroup 파일 읽기 실패")
    
    # 4. 현재 작업 디렉토리
    print(f"\n작업 디렉토리:")
    print(f"  현재 경로: {os.getcwd()}")
    print(f"  프로젝트 경로: {os.path.dirname(os.path.abspath(__file__))}")
    
    # 5. 시스템 명령어 확인
    print(f"\n시스템 명령어 확인:")
    
    # which 명령어로 chromium 확인
    try:
        result = subprocess.run(['which', 'chromium'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"  chromium 경로: {result.stdout.strip()}")
        else:
            print("  chromium: 설치되지 않음")
    except:
        print("  chromium: 확인 실패")
    
    # google-chrome 확인
    try:
        result = subprocess.run(['which', 'google-chrome'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"  google-chrome 경로: {result.stdout.strip()}")
        else:
            print("  google-chrome: 설치되지 않음")
    except:
        print("  google-chrome: 확인 실패")
    
    # 6. 환경 변수 확인
    print(f"\n환경 변수:")
    print(f"  PATH: {os.environ.get('PATH', 'N/A')[:100]}...")
    print(f"  HOME: {os.environ.get('HOME', 'N/A')}")
    print(f"  USER: {os.environ.get('USER', 'N/A')}")
    
    # 7. 프로세스 확인
    print(f"\n프로세스 확인:")
    try:
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        if 'docker' in result.stdout.lower():
            print("  Docker 관련 프로세스 발견")
        else:
            print("  Docker 관련 프로세스 없음")
    except:
        print("  프로세스 확인 실패")

def check_docker_status():
    """Docker 상태 확인"""
    print("\n" + "=" * 60)
    print("Docker 상태 확인")
    print("=" * 60)
    
    try:
        # docker 명령어 실행 가능한지 확인
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"Docker 버전: {result.stdout.strip()}")
        else:
            print("Docker 명령어 실행 불가")
    except:
        print("Docker 명령어 없음")
    
    try:
        # docker ps 실행
        result = subprocess.run(['docker', 'ps'], capture_output=True, text=True)
        if result.returncode == 0:
            print("실행 중인 컨테이너:")
            print(result.stdout)
        else:
            print("Docker 컨테이너 확인 실패")
    except:
        print("Docker 컨테이너 확인 불가")

if __name__ == "__main__":
    check_environment()
    check_docker_status()