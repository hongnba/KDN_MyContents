import fitz  # PyMuPDF
from ksubscribe_server.summarize.gpt_summarize import GPTSummarize
from ksubscribe_server.summarize.ollama_summarize import OllamaSummarize

class PdfSummarize:
    
    def __init__(self):
        self.gptSummarize = GPTSummarize()
        self.ollamaSummarize = OllamaSummarize()
        pass    
    
    def extract_text_from_pdf(self, pdf_path, max_chunk_size=2000):
        """
        PDF에서 텍스트를 추출하고, 청크로 나눔
        """
        doc = fitz.open(pdf_path)
        text = ""
        
        # PDF 전체 텍스트 추출
        for page in doc:
            text += page.get_text()

        # 텍스트를 청크로 나누기
        chunks = []
        while len(text) > max_chunk_size:
            split_index = text[:max_chunk_size].rfind(" ")
            chunks.append(text[:split_index])
            text = text[split_index:]
        chunks.append(text)  # 마지막 청크 추가

        return chunks
    
    def summarize_pdf_by_gpt(self, pdf_path):
        # 1. PDF에서 텍스트 추출 및 청크 나누기
        chunks = self.extract_text_from_pdf(pdf_path)

        # 2. 각 청크 요약
        all_summaries = []
        for i, chunk in enumerate(chunks):
            print(f"Summarizing chunk {i + 1}/{len(chunks)}...")
            summary = self.gptSummarize.summarize_chunk(chunk)
            if summary:
                all_summaries.append(summary)

        # 3. 최종 요약 생성
        final_summary = self.gptSummarize.summarize_chunk(" ".join(all_summaries))
        return final_summary   
    
     