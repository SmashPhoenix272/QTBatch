import vertexai
from vertexai.generative_models import GenerativeModel, HarmCategory, HarmBlockThreshold
from typing import List, Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_fixed

class VertexAIProvider:
    def __init__(self, project_id: str, location: str, model: str):
        self.project_id = project_id
        self.location = location
        self.model = model
        vertexai.init(project=project_id, location=location)
        self.generative_model = GenerativeModel(model)

    def estimate_token_count(self, text: str) -> int:
        # Vertex AI doesn't provide a direct method to count tokens
        # This is a rough estimate based on word count
        return len(text.split())

    def calculate_cost(self, input_tokens: int, output_tokens: int, context_length: int = 0) -> float:
        input_cost = 0
        output_cost = 0

        if self.model == "gemini-1.5-flash":
            if context_length <= 128000:
                input_cost = input_tokens * 0.00001875 / 1000
                output_cost = output_tokens * 0.000075 / 1000
            else:
                input_cost = input_tokens * 0.0000375 / 1000
                output_cost = output_tokens * 0.00015 / 1000
        elif self.model == "gemini-1.5-pro":
            if context_length <= 128000:
                input_cost = input_tokens * 0.00125 / 1000
                output_cost = output_tokens * 0.00375 / 1000
            else:
                input_cost = input_tokens * 0.0025 / 1000
                output_cost = output_tokens * 0.0075 / 1000
        elif self.model == "gemini-1.0-pro":
            input_cost = input_tokens * 0.000125 / 1000
            output_cost = output_tokens * 0.000375 / 1000

        return input_cost + output_cost

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def generate_content(self, prompt: str, safety_settings: Optional[List[Dict]] = None, stream: bool = False) -> Any:
        if safety_settings is None:
            safety_settings = [
                {
                    "category": HarmCategory.HARM_CATEGORY_HARASSMENT,
                    "threshold": HarmBlockThreshold.BLOCK_NONE
                },
                {
                    "category": HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    "threshold": HarmBlockThreshold.BLOCK_NONE
                },
                {
                    "category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    "threshold": HarmBlockThreshold.BLOCK_NONE
                },
                {
                    "category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    "threshold": HarmBlockThreshold.BLOCK_NONE
                }
            ]

        response = self.generative_model.generate_content(
            prompt,
            safety_settings=safety_settings,
            stream=stream
        )

        if stream:
            return response
        else:
            return response.text

    def get_usage_metadata(self, response) -> Dict[str, int]:
        return {
            "prompt_token_count": response.prompt_token_count,
            "candidates_token_count": response.candidates_token_count,
            "total_token_count": response.total_token_count
        }