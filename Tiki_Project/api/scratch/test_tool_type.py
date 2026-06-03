import google.generativeai as genai
import google.ai.generativelanguage as glm

fd = glm.FunctionDeclaration(
    name="recommend_business",
    description="Recommend business ideas based on capital",
    parameters=glm.Schema(
        type=glm.Type.OBJECT,
        properties={
            "capital": glm.Schema(type=glm.Type.NUMBER, description="Vốn đầu tư dự kiến (VND)"),
            "location": glm.Schema(type=glm.Type.STRING, description="Địa điểm kinh doanh (TP.HCM)"),
            "interest": glm.Schema(type=glm.Type.STRING, description="Lĩnh vực sắm"),
            "experience": glm.Schema(type=glm.Type.STRING, description="Kinh nghiệm")
        },
        required=["capital"]
    )
)

try:
    tool = glm.Tool(function_declarations=[fd])
    print("glm.Tool successfully constructed!")
    
    # Try passing to GenerativeModel
    model = genai.GenerativeModel(
        model_name="gemini-flash-latest",
        tools=[tool]
    )
    print("genai.GenerativeModel successfully created with tool!")
except Exception as e:
    import traceback
    traceback.print_exc()
