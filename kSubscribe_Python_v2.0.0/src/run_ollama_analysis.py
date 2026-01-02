#!/usr/bin/env python3
"""
새로 추가된 문서에 대해 Ollama 분석만 실행하는 스크립트
rawCollectSucYN="Y"이고 metaSucYN="N"인 문서를 찾아서 Ollama 5가지 업무 수행
"""
import sys
import os
from datetime import datetime

# 프로젝트 경로 추가
sys.path.insert(0, '/app')

from docker_scraping.contents_scraping_ollama_trafilaura import ContentsScrapingOllamaTrafilaura
from ksubscribe_share.db.service.contentsService import ContentsService
from ksubscribe_server.analysis.analysis_ollama_generate import AnalysisOllamaGenerateCall

def main():
    print("=" * 80)
    print("Ollama 분석 시작: rawCollectSucYN='Y', metaSucYN='N' 인 문서 처리")
    print("=" * 80)
    
    # 서비스 인스턴스 생성
    contentsService = ContentsService()
    analysisOllama = AnalysisOllamaGenerateCall()
    
    # rawCollectSucYN='Y'이고 metaSucYN='N' 또는 None인 문서 조회
    print("\n🔍 분석 대상 문서 검색 중...")
    print("📌 조건: rawCollectSucYN='Y' AND metaSucYN IN ('N', None)")
    
    contentsVOList = contentsService.findContents_rawCollectSucYN_is_true(-1)
    
    if len(contentsVOList) <= 0:
        print("❌ 분석 대상 문서가 없습니다.")
        return
    
    print(f"✅ 분석 대상 문서 {len(contentsVOList)}건 발견\n")
    
    # 각 문서에 대해 Ollama 분석 수행
    for index, contentsVO in enumerate(contentsVOList):
        print(f"\n{'='*80}")
        print(f"📝 [{index+1}/{len(contentsVOList)}] 문서 분석 중...")
        print(f"   제목: {contentsVO.title[:50]}...")
        print(f"   URL: {contentsVO.url}")
        print(f"{'='*80}")
        
        try:
            # Ollama로 5가지 분석 수행
            contentsVO.metaAnalyzeDt = datetime.now()
            analysisOllama.analysis_main(contentsVO)
            
            # MongoDB 업데이트
            contentsService.save(contentsVO)
            
            print(f"✅ 분석 완료!")
            
        except Exception as e:
            print(f"❌ 분석 실패: {str(e)}")
            import traceback
            traceback.print_exc()
            continue
    
    print("\n" + "=" * 80)
    print(f"🎉 전체 분석 완료: {len(contentsVOList)}건 처리")
    print("=" * 80)

if __name__ == "__main__":
    main()
