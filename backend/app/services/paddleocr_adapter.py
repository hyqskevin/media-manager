from pathlib import Path
from threading import Lock
from app.core.config import Settings

class PaddleOCREngine:
    _instance=None; _lock=Lock()
    def __new__(cls,settings:Settings):
        with cls._lock:
            if cls._instance is None:
                obj=super().__new__(cls); obj._init(settings); cls._instance=obj
        return cls._instance
    def _init(self,settings):
        try: from paddleocr import PaddleOCR
        except ImportError as exc: raise RuntimeError('Install PaddleOCR using docs/paddleocr-setup.md') from exc
        self.ocr=PaddleOCR(lang=settings.ocr_language,use_doc_orientation_classify=settings.ocr_use_doc_orientation_classify,use_doc_unwarping=settings.ocr_use_doc_unwarping,use_textline_orientation=settings.ocr_use_textline_orientation)
    def __call__(self,path:Path)->list[tuple[str,float]]:
        results=self.ocr.predict(str(path)); lines=[]
        for result in results:
            data=getattr(result,'json',result)
            if callable(data): data=data()
            payload=data.get('res',data) if isinstance(data,dict) else {}
            lines.extend(zip(payload.get('rec_texts',[]),payload.get('rec_scores',[])))
        return [(str(t),float(s)) for t,s in lines]
