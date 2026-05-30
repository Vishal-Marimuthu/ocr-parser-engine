import cv2
import numpy as np
import os

def create_mock_invoice():
    # Create a white image
    width, height = 800, 1000
    img = np.ones((height, width, 3), dtype=np.uint8) * 255
    
    # Fonts
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_bold = cv2.FONT_HERSHEY_TRIPLEX
    
    # Add noise / artifact simulation (Optional but good for OCR test)
    noise = np.random.randint(0, 50, (height, width, 3), dtype=np.uint8)
    img = cv2.subtract(img, noise)
    
    # Header
    cv2.putText(img, 'ACME Corporation', (50, 100), font_bold, 1.5, (0, 0, 0), 2)
    cv2.putText(img, '123 Business Rd.', (50, 140), font, 0.7, (0, 0, 0), 1)
    cv2.putText(img, 'Metropolis, NY 10001', (50, 170), font, 0.7, (0, 0, 0), 1)
    
    # INVOICE title
    cv2.putText(img, 'INVOICE', (550, 100), font_bold, 1.5, (50, 50, 50), 2)
    
    # Details
    cv2.putText(img, 'Date: Oct 25, 2023', (550, 150), font, 0.8, (0, 0, 0), 1)
    cv2.putText(img, 'Invoice #: INV-987654', (550, 180), font, 0.8, (0, 0, 0), 1)
    
    # Divider
    cv2.line(img, (50, 220), (750, 220), (0, 0, 0), 2)
    
    # Table headers
    cv2.putText(img, 'Description', (50, 260), font_bold, 0.8, (0, 0, 0), 1)
    cv2.putText(img, 'Amount', (650, 260), font_bold, 0.8, (0, 0, 0), 1)
    cv2.line(img, (50, 280), (750, 280), (0, 0, 0), 1)
    
    # Items
    cv2.putText(img, 'Web Development Services', (50, 320), font, 0.7, (0, 0, 0), 1)
    cv2.putText(img, '$2,500.00', (650, 320), font, 0.7, (0, 0, 0), 1)
    
    cv2.putText(img, 'Cloud Hosting (1 Year)', (50, 370), font, 0.7, (0, 0, 0), 1)
    cv2.putText(img, '$350.50', (650, 370), font, 0.7, (0, 0, 0), 1)
    
    cv2.putText(img, 'Maintenance & Support', (50, 420), font, 0.7, (0, 0, 0), 1)
    cv2.putText(img, '$1,200.00', (650, 420), font, 0.7, (0, 0, 0), 1)
    
    # Divider
    cv2.line(img, (50, 460), (750, 460), (0, 0, 0), 1)
    
    # Total
    cv2.putText(img, 'Subtotal:', (500, 510), font, 0.8, (0, 0, 0), 1)
    cv2.putText(img, '$4,050.50', (650, 510), font, 0.8, (0, 0, 0), 1)
    
    cv2.putText(img, 'Tax (8%):', (500, 550), font, 0.8, (0, 0, 0), 1)
    cv2.putText(img, '$324.04', (650, 550), font, 0.8, (0, 0, 0), 1)
    
    cv2.putText(img, 'Total Amount:', (450, 610), font_bold, 1.0, (0, 0, 0), 2)
    cv2.putText(img, '$4,374.54', (620, 610), font_bold, 1.0, (0, 0, 0), 2)
    
    # Footer
    cv2.putText(img, 'Thank you for your business!', (200, 900), font_bold, 0.8, (100, 100, 100), 1)
    
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'public')
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, 'sample_invoice.png')
    
    cv2.imwrite(out_path, img)
    print(f"Generated sample invoice at: {out_path}")

if __name__ == "__main__":
    create_mock_invoice()
