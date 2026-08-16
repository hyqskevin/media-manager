from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from time import sleep
from typing import Callable


OCREngine = Callable[[Path], list[tuple[str, float]]]


class OCRService:
    def __init__(self, engine: OCREngine, min_confidence: float = 0.5) -> None:
        self.engine = engine
        self.min_confidence = min_confidence

    def process(self, image: Path) -> dict[str, str]:
        try:
            lines = self.engine(image)
            text = "\n".join(value for value, confidence in lines if confidence >= self.min_confidence)
            return {"status": "success", "text": text, "error": ""}
        except Exception as exc:
            return {"status": "failed", "text": "", "error": str(exc)}

    def process_many(self, images: list[Path]) -> list[dict[str, str]]:
        return [self.process(image) for image in images]

    def process_batch(
        self,
        images: list[Path],
        workers: int = 2,
        attempts: int = 1,
        delay: float = 0.0,
    ) -> list[dict[str, str]]:
        """并行处理多张图片，按输入顺序返回结果。

        workers=1 时退化为串行（等价于 process_many）。
        attempts>1 时每张图片在子线程内重试（OCR 失败重试，不致命）。
        PaddleOCR 单例 predict 线程安全，本地模型不占网络带宽。
        """

        def process_with_retry(image: Path) -> dict[str, str]:
            if attempts <= 1:
                return self.process(image)
            last_result: dict[str, str] = {"status": "failed", "text": "", "error": "not executed"}
            for _ in range(max(1, attempts)):
                last_result = self.process(image)
                if last_result["status"] != "failed":
                    return last_result
                sleep(delay)
            return last_result

        if workers <= 1 or len(images) <= 1:
            return [process_with_retry(image) for image in images]

        results: list[dict[str, str] | None] = [None] * len(images)
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_index = {
                executor.submit(process_with_retry, image): idx
                for idx, image in enumerate(images)
            }
            for future in as_completed(future_to_index):
                idx = future_to_index[future]
                results[idx] = future.result()
        return [r if r is not None else {"status": "failed", "text": "", "error": "unknown"} for r in results]
