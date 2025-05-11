import zipfile
import os
import rasterio
from rasterio.plot import reshape_as_image
from PIL import Image

def process_sentinel_zip(zip_path):
    # Ottieni la cartella in cui si trova lo zip
    zip_dir = os.path.dirname(zip_path)
    
    # Estrai lo zip nella stessa cartella
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(zip_dir)
    
    # Trova la cartella estratta (assume che ci sia solo una cartella grande dentro lo zip)
    extracted_folders = [f for f in os.listdir(zip_dir) if os.path.isdir(os.path.join(zip_dir, f))]
    extracted_folders.sort(key=lambda f: os.path.getmtime(os.path.join(zip_dir, f)), reverse=True)
    
    for folder in extracted_folders:
        folder_path = os.path.join(zip_dir, folder)
        # Cerca il file TCI (di solito ha "TCI" nel nome e termina con .jp2)
        for root, _, files in os.walk(folder_path):
            for file in files:
                if 'TCI' in file and file.endswith('.jp2'):
                    tci_path = os.path.join(root, file)
                    print(f"Trovato file TCI: {tci_path}")
                    return convert_to_png(tci_path, zip_dir)

    print("File TCI non trovato.")
    return None

def convert_to_png(tci_path, output_dir):
    with rasterio.open(tci_path) as src:
        img = src.read()
        img = reshape_as_image(img)  # Risistema da (3, H, W) a (H, W, 3)
        img = Image.fromarray(img)
        png_path = os.path.join(output_dir, 'TCI_converted.png')
        img.save(png_path)
        print(f"Immagine PNG salvata in: {png_path}")
        return png_path

# Esempio di uso:
zip_path= 
process_sentinel_zip(zip_path)