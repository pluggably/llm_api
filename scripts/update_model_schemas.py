#!/usr/bin/env python3
"""Script to add parameter schema for image models."""
import sqlite3
import json

# Standard parameter schema for Stable Diffusion XL
sdxl_schema = {
    "type": "object",
    "properties": {
        "num_inference_steps": {
            "type": "integer",
            "description": "Number of denoising steps. More steps = higher quality but slower.",
            "default": 50,
            "minimum": 1,
            "maximum": 150
        },
        "guidance_scale": {
            "type": "number",
            "description": "How strongly the image should conform to the prompt. Higher = more literal.",
            "default": 7.5,
            "minimum": 1.0,
            "maximum": 20.0
        },
        "width": {
            "type": "integer",
            "description": "Image width in pixels. Must be divisible by 8.",
            "default": 1024,
            "minimum": 512,
            "maximum": 2048
        },
        "height": {
            "type": "integer",
            "description": "Image height in pixels. Must be divisible by 8.",
            "default": 1024,
            "minimum": 512,
            "maximum": 2048
        },
        "negative_prompt": {
            "type": "string",
            "description": "What to avoid in the image."
        },
        "seed": {
            "type": "integer",
            "description": "Random seed for reproducibility."
        }
    }
}

# Standard parameter schema for 3D models (shap-e)
shape_schema = {
    "type": "object",
    "properties": {
        "guidance_scale": {
            "type": "number",
            "description": "How strongly the mesh should conform to the prompt.",
            "default": 3.0,
            "minimum": 1.0,
            "maximum": 15.0
        },
        "batch_size": {
            "type": "integer",
            "description": "Number of variations to generate.",
            "default": 1,
            "minimum": 1,
            "maximum": 4
        }
    }
}

def main():
    conn = sqlite3.connect("models/llm_api.db")
    cursor = conn.cursor()
    
    # Update SD XL model
    cursor.execute(
        "UPDATE models SET parameter_schema = ? WHERE id = ?",
        (json.dumps(sdxl_schema), "stabilityai/stable-diffusion-xl-base-1.0")
    )
    print(f"Updated SD XL: {cursor.rowcount} row(s)")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    main()
