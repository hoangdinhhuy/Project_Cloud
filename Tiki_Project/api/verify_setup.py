"""
Quick verification script to check if setup is correct
Run this BEFORE starting the API server
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

def check_file(path: Path, name: str) -> bool:
    """Check if file exists"""
    exists = path.exists()
    icon = "✅" if exists else "❌"
    print(f"{icon} {name}: {path}")
    return exists

def check_file_alternatives(paths: list, name: str) -> bool:
    """Check if any of the alternative paths exist"""
    for path in paths:
        if path.exists():
            print(f"✅ {name}: {path}")
            return True
    # None found
    print(f"❌ {name}: tried {len(paths)} locations")
    for path in paths:
        print(f"   - {path}")
    return False

def check_size(path: Path, name: str, min_mb: float) -> bool:
    """Check if file size is reasonable"""
    if not path.exists():
        return False
    
    size_mb = path.stat().st_size / (1024 * 1024)
    ok = size_mb >= min_mb
    icon = "✅" if ok else "⚠️"
    print(f"{icon} {name} size: {size_mb:.2f} MB (expected >= {min_mb} MB)")
    return ok

def main():
    print("=" * 60)
    print("🔍 TIKI API SETUP VERIFICATION")
    print("=" * 60)
    
    # Load .env
    load_dotenv()
    
    issues = []
    
    # 1. Check .env file
    print("\n📄 Checking .env configuration...")
    if not Path('.env').exists():
        print("❌ .env file not found!")
        print("   → Copy .env.example to .env and configure it")
        issues.append(".env file missing")
    else:
        print("✅ .env file found")
        
        # Check GEMINI_API_KEY (PRIMARY provider for chat)
        gemini_key = os.getenv('GEMINI_API_KEY', '')
        if gemini_key:
            key_count = len([k for k in gemini_key.split(',') if k.strip()])
            print(f"✅ GEMINI_API_KEY: {key_count} key(s) configured [PRIMARY CHAT PROVIDER]")
        else:
            print("❌ GEMINI_API_KEY not set in .env (required for chat!)")
            issues.append("GEMINI_API_KEY not configured (primary chat provider)")
        
        # Check data path vars
        for var in ['DATA_PATH', 'MODELS_PATH', 'CHROMA_DB_PATH']:
            value = os.getenv(var)
            if not value:
                print(f"❌ {var} not set in .env")
                issues.append(f"{var} not configured")
            else:
                print(f"✅ {var}: {value}")
    
    # 2. Check data files
    print("\n📦 Checking data files...")
    data_path = Path(os.getenv('DATA_PATH', './data'))
    
    files_to_check = [
        (data_path / 'products.json', 'Products data', 1.0),
        (data_path / 'reviews.json', 'Reviews data', 15.0),
        (data_path / 'timeseries.json', 'Timeseries data', 0.1),
    ]
    
    for file_path, name, min_size in files_to_check:
        if not check_file(file_path, name):
            issues.append(f"{name} file missing")
        else:
            check_size(file_path, name, min_size)
    
    # 3. Check model files (support multiple naming conventions)
    print("\n🤖 Checking model files...")
    models_path = Path(os.getenv('MODELS_PATH', './models'))
    
    # KMeans - try multiple locations
    kmeans_paths = [
        models_path / 'kmeans' / 'kmeans_model.pkl',
        models_path / 'k_mean' / 'kmeans_model_20260419_100129_model.pkl',
        models_path / 'KMeans_Clustering' / 'kmeans_model.pkl',
        models_path / 'KMeans_Clustering' / 'kmeans_model_20260419_100129_model.pkl',
        models_path / 'KMeans_Clustering' / 'KMeans_Clustering_Final' / 'kmeans_model_20260419_150808_metadata.json',
        models_path / 'KMeans_Clustering' / 'KMeans_Clustering_Final' / 'cluster_profiles.csv',
    ]
    # Also check for any .pkl in KMeans folders
    for folder_name in ['kmeans', 'k_mean', 'KMeans_Clustering']:
        folder = models_path / folder_name
        if folder.exists() and folder.is_dir():
            kmeans_paths.extend(folder.glob('*.pkl'))
            kmeans_paths.extend(folder.glob('*.json'))
            kmeans_paths.extend(folder.glob('*.csv'))
    
    if not check_file_alternatives(list(set(kmeans_paths)), 'KMeans model'):
        issues.append("KMeans model missing")
    
    # Prophet - try multiple locations
    prophet_folders = [
        models_path / 'Prophet',
        models_path / 'prophet',
        models_path / 'Prophet_models',
    ]
    
    prophet_folder = None
    for folder in prophet_folders:
        if folder.exists():
            prophet_folder = folder
            break
    
    if prophet_folder:
        # Check if it's the Prophet_models folder, which has a subfolder prophet_models
        subfolder = 'prophet_models' if prophet_folder.name == 'Prophet_models' else ''
        prophet_subfolder = prophet_folder / subfolder
        if prophet_subfolder.exists():
            print(f"✅ Prophet folder: {prophet_subfolder}")
            # Assume models are available if folder exists
        else:
            print(f"❌ Prophet subfolder not found: {prophet_subfolder}")
            issues.append("Prophet models directory missing")
    else:
        print(f"❌ Prophet folder not found (tried: Prophet, prophet, Prophet_models)")
        issues.append("Prophet models directory missing")
    
    # PhoBERT - try multiple locations
    phobert_folders = [
        models_path / 'PhoBert',
        models_path / 'phobert',
        models_path / 'Phobert_model',
    ]
    
    phobert_folder = None
    for folder in phobert_folders:
        if folder.exists():
            phobert_folder = folder
            break
    
    if phobert_folder:
        phobert_files = [
            ('config.json', 'PhoBERT config'),
            ('tokenizer_config.json', 'PhoBERT tokenizer'),
        ]
        
        for filename, name in phobert_files:
            file_path = phobert_folder / filename
            if not check_file(file_path, name):
                issues.append(f"{name} missing")
    else:
        print(f"❌ PhoBERT folder not found (tried: PhoBert, phobert, Phobert_model)")
        issues.append("PhoBERT directory missing")
    
    # 4. Check ChromaDB
    print("\n💾 Checking ChromaDB...")
    chroma_path = Path(os.getenv('CHROMA_DB_PATH', './chroma_db'))
    if not check_file(chroma_path, 'ChromaDB directory'):
        issues.append("ChromaDB directory missing")
    else:
        # Check if it has data
        try:
            files_in_chroma = list(chroma_path.iterdir())
            if not files_in_chroma:
                print("⚠️  ChromaDB directory is empty!")
                issues.append("ChromaDB is empty")
            else:
                print(f"✅ ChromaDB has {len(files_in_chroma)} files")
        except Exception as e:
            print(f"⚠️  Could not list ChromaDB contents: {e}")
    
    # 5. Check Python packages
    print("\n📚 Checking Python packages...")
    required_packages = [
        ('fastapi', 'fastapi', True),
        ('uvicorn', 'uvicorn', True),
        ('groq', 'groq', False),
        ('chromadb', 'chromadb', True),
        ('sentence_transformers', 'sentence_transformers', True),
        ('google.generativeai', 'google.generativeai', False),
        ('sklearn', 'sklearn', True),
        ('prophet', 'prophet', False),
        ('torch', 'torch', True),
        ('transformers', 'transformers', True),
    ]
    
    missing_packages = []
    for display_name, import_name, is_required in required_packages:
        try:
            __import__(import_name)
            label = '' if is_required else ' (optional)'
            print(f"✅ {display_name}{label}")
        except ImportError:
            if is_required:
                print(f"❌ {display_name} not installed")
                missing_packages.append(display_name)
                issues.append(f"Package {display_name} missing")
            else:
                print(f"⚠️  {display_name} not installed (optional)")
    
    # 6. Summary
    print("\n" + "=" * 60)
    if not issues:
        print("✅ ALL CHECKS PASSED!")
        print("=" * 60)
        print("\n🚀 You can now start the server:")
        print("   python main.py")
        return 0
    else:
        print("❌ ISSUES FOUND:")
        print("=" * 60)
        for i, issue in enumerate(issues, 1):
            print(f"{i}. {issue}")
        print("\n📖 Please fix these issues before starting the server.")
        print("   See DEPLOYMENT_GUIDE.md for detailed instructions.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
