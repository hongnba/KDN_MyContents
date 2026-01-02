
import sys
import os
from pathlib import Path

# Add src to path
sys.path.append("/home/themiraclesoft/mycontents/KDN_MyContents/kSubscribe_Python_v2.0.0/src")

from ksubscribe_share.db.service.contentsOrgService import ContentsOrgService

def check_org(org_id):
    print(f"Checking orgId: {org_id}")
    service = ContentsOrgService()
    orgName, keywords = service.getOrgNameAndKeywords(org_id)
    print(f"Result: orgName='{orgName}', keywords={keywords}")

if __name__ == "__main__":
    check_org("A0010")
