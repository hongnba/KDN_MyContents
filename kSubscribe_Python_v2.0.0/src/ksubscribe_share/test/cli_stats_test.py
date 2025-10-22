#!/usr/bin/env python3
"""
Stats Test - 기관 평판 통계 계산 도구
orgId와 period를 인자로 받아서 통계를 계산하고 데이터베이스에 저장
"""

import sys
import os
from datetime import datetime

# Add the current directory to the Python path (when running from src directory)
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ksubscribe_share.db.service.statsService import StatsService
from ksubscribe_share.db.service.contentsOrgService import ContentsOrgService
from ksubscribe_share.db.service.calendarService import CalendarService


def calculate_stats_for_org(orgId: str, period: str = "day"):
    """
    특정 기관의 통계 계산 및 데이터베이스 저장
    
    Args:
        orgId: 기관 ID
        period: 기간 ("day", "week", "month")
    
    Returns:
        Dict: 통계 결과
    """
    print(f"\n=== {orgId} 기관 통계 계산 및 저장 ({period}) ===")
    
    try:
        stats_service = StatsService()
        calendar_service = CalendarService()
        
        # 통계 계산 및 데이터베이스에 저장
        print(f"📊 통계 계산 중...")
        stats = stats_service.count_for_period(orgId, period)
        
        # 캘린더 결과 계산 및 저장
        print(f"📅 캘린더 결과 계산 중...")
        calendar_results = calendar_service.get_calendar_results(orgId)
        
        # 저장된 통계 객체 정보 출력
        print(f"💾 데이터베이스에 저장됨:")
        print(f"  - 통계 ID: {stats._id}")
        print(f"  - 기관 ID: {stats.orgId}")
        print(f"  - 기간: {stats.period}")
        print(f"  - 계산일시: {stats.last_calculate_date}")
        
        # 향상된 통계 요약 정보 조회
        enhanced_summary = stats_service.get_enhanced_stats_summary(orgId, period)
        
        # 캘린더 결과를 enhanced_summary에 추가
        enhanced_summary['positiveResult'] = calendar_results['positiveResult']
        enhanced_summary['negativeResult'] = calendar_results['negativeResult']
        enhanced_summary['neutralResult'] = calendar_results['neutralResult']
        
        print(f"✅ 통계 계산 및 저장 완료:")
        print(f"  - 총 기사 수: {enhanced_summary['totalContentsCounts']}")
        print(f"  - 긍정 비율: {enhanced_summary['averagePositiveRatio']:.2f}%")
        print(f"  - 부정 비율: {enhanced_summary['averageNegativeRatio']:.2f}%")
        print(f"  - 중립 비율: {enhanced_summary['averageNeutralRatio']:.2f}%")
        print(f"  - 긍정 키워드: {enhanced_summary['totalPositiveKeywordList'][:3]}")
        print(f"  - 부정 키워드: {enhanced_summary['totalNegativeKeywordList'][:3]}")
        print(f"  - 긍정 기사 수: {len(enhanced_summary['positiveSortedMap'])}")
        print(f"  - 부정 기사 수: {len(enhanced_summary['negativeSortedMap'])}")
        
        if enhanced_summary['ollamaReputationChangeReason']:
            print(f"  - Ollama 분석: {enhanced_summary['ollamaReputationChangeReason'][:100]}...")
        
        # 캘린더 결과 출력
        print(f"📅 캘린더 결과:")
        print(f"  - 긍정 결과: {len(calendar_results['positiveResult'])} 일")
        print(f"  - 부정 결과: {len(calendar_results['negativeResult'])} 일")
        print(f"  - 중립 결과: {len(calendar_results['neutralResult'])} 일")
        
        # 최근 3일 결과 출력
        recent_days = sorted(calendar_results['positiveResult'].keys())[-3:]
        for day in recent_days:
            pos = calendar_results['positiveResult'].get(day, -99.0)
            neg = calendar_results['negativeResult'].get(day, -99.0)
            neu = calendar_results['neutralResult'].get(day, -99.0)
            print(f"    {day}: 긍정 {pos:.1f}%, 부정 {neg:.1f}%, 중립 {neu:.1f}%")
        
        return enhanced_summary
        
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        return None


def get_org_list():
    """
    기관 목록 조회
    
    Returns:
        List: 기관 목록
    """
    try:
        contents_org_service = ContentsOrgService()
        all_orgs = contents_org_service.find_all()
        
        if not all_orgs:
            print("❌ 기관 목록을 찾을 수 없습니다.")
            return []
        
        print(f"📋 기관 목록 ({len(all_orgs)}개):")
        for i, org in enumerate(all_orgs, 1):
            print(f"  {i}. {org.orgName} ({org.orgId})")
        
        return all_orgs
        
    except Exception as e:
        print(f"❌ 기관 목록 조회 오류: {str(e)}")
        return []


def main():
    """메인 함수"""
    print("🚀 기관 평판 통계 계산 도구")
    
    # 1. 기관 목록 조회 및 표시
    print("\n1. 기관 목록 조회")
    orgs = get_org_list()
    
    if not orgs:
        print("❌ 기관이 없어서 종료합니다.")
        return
    
    # 2. 사용자 입력 받기
    print(f"\n2. 기관 선택")
    print("기관 번호를 입력하세요 (0: 모든 기관, 1-{len(orgs)}: 특정 기관):")
    
    try:
        choice = int(input("선택: ").strip())
    except ValueError:
        print("❌ 잘못된 입력입니다. 숫자를 입력하세요.")
        return
    
    if choice < 0 or choice > len(orgs):
        print(f"❌ 잘못된 선택입니다. 0-{len(orgs)} 사이의 숫자를 입력하세요.")
        return
    
    # 3. 기간 선택
    print(f"\n3. 기간 선택")
    print("기간을 선택하세요 (1: day, 2: week, 3: month):")
    
    try:
        period_choice = int(input("선택: ").strip())
    except ValueError:
        print("❌ 잘못된 입력입니다. 숫자를 입력하세요.")
        return
    
    period_map = {1: "day", 2: "week", 3: "month"}
    if period_choice not in period_map:
        print("❌ 잘못된 선택입니다. 1-3 사이의 숫자를 입력하세요.")
        return
    
    period = period_map[period_choice]
    print(f"선택된 기간: {period}")
    
    # 4. 통계 계산
    print(f"\n4. 통계 계산 시작")
    
    if choice == 0:
        # 모든 기관 처리
        print(f"🌍 모든 기관 처리: {period}")
        results = []
        success_count = 0
        
        for i, org in enumerate(orgs, 1):
            print(f"\n[{i}/{len(orgs)}] 처리 중: {org.orgName} ({org.orgId})")
            
            try:
                result = calculate_stats_for_org(org.orgId, period)
                if result:
                    result['orgName'] = org.orgName
                    results.append(result)
                    success_count += 1
                else:
                    print(f"  ⚠️  {org.orgName} 통계 계산 실패")
            except Exception as e:
                print(f"  ❌ {org.orgName} 오류: {str(e)}")
                continue
        
        # 결과 요약
        if results:
            print(f"\n📈 결과 요약 ({success_count}/{len(orgs)} 기관 처리됨):")
            total_articles = sum(r.get('totalContentsCounts', 0) for r in results)
            avg_positive = sum(r.get('averagePositiveRatio', 0) for r in results) / len(results)
            avg_negative = sum(r.get('averageNegativeRatio', 0) for r in results) / len(results)
            
            print(f"  - 총 기사 수: {total_articles}")
            print(f"  - 평균 긍정 비율: {avg_positive:.2f}%")
            print(f"  - 평균 부정 비율: {avg_negative:.2f}%")
            
            # 상위 3개 기관 출력
            print(f"\n🏆 상위 3개 기관:")
            sorted_results = sorted(results, key=lambda x: x.get('totalContentsCounts', 0), reverse=True)
            for i, result in enumerate(sorted_results[:3], 1):
                print(f"  {i}. {result['orgName']}: {result.get('totalContentsCounts', 0)}개 기사, "
                      f"긍정 {result.get('averagePositiveRatio', 0):.1f}%")
        else:
            print("❌ 처리된 기관이 없습니다.")
    
    else:
        # 특정 기관 처리
        selected_org = orgs[choice - 1]
        print(f"🎯 특정 기관 처리: {selected_org.orgName} ({selected_org.orgId})")
        
        result = calculate_stats_for_org(selected_org.orgId, period)
        
        if result:
            print(f"\n✅ {selected_org.orgName} 통계 계산 완료")
        else:
            print(f"\n❌ {selected_org.orgName} 통계 계산 실패")
    
    print("\n✅ 테스트 완료!")


if __name__ == "__main__":
    main()
