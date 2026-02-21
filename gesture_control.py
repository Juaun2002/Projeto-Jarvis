# gesture_control.py - Controle por gestos refinado (OpenCV)
import cv2
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap

class GestureThread(QThread):
    """Thread para detectar gestos com OpenCV"""
    frame_ready = pyqtSignal(QPixmap)
    gesture_detected = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.running = False
        self.frame_count = 0
        self.last_gesture = None
        self.gesture_cooldown = 0
        self.gesture_confidence = 0
        self.gesture_history = []  # Histórico para consistência
        self.brightness_avg = 128  # Média de brilho para ajuste adaptativo
        
        # HSV para detecção de pele - duplo range para cobrir mais tons
        self.lower_skin_1 = np.array([0, 20, 70], dtype=np.uint8)
        self.upper_skin_1 = np.array([20, 170, 255], dtype=np.uint8)
        self.lower_skin_2 = np.array([0, 10, 50], dtype=np.uint8)  # Tons mais escuros
        self.upper_skin_2 = np.array([25, 180, 230], dtype=np.uint8)
        
        # Cores JARVIS
        self.COLORS = {
            'primary': (0, 255, 255),
            'secondary': (0, 200, 255),
            'background': (0, 8, 20),
            'text': (0, 255, 255),
        }
        
    def run(self):
        """Loop principal"""
        self.running = True
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # DirectShow mais rápido no Windows
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 60)  # Tentar 60fps
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)  # Autofoco
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)  # Auto-exposição
        cap.set(cv2.CAP_PROP_BRIGHTNESS, 0.55)  # Brilho aumentado
        cap.set(cv2.CAP_PROP_CONTRAST, 0.6)  # Contraste aumentado
        
        while self.running:
            ret, frame = cap.read()
            if not ret:
                continue
            
            frame = cv2.flip(frame, 1)
            processed_frame, gesture = self.process_frame(frame)
            
            # Validação por histórico (3 frames consecutivos)
            self.gesture_history.append(gesture)
            if len(self.gesture_history) > 3:
                self.gesture_history.pop(0)
            
            # Só emite se gesto aparecer 3x seguidas
            if len(self.gesture_history) == 3 and \
               self.gesture_history[0] == self.gesture_history[1] == self.gesture_history[2] and \
               gesture and gesture != self.last_gesture and self.gesture_cooldown == 0:
                self.gesture_detected.emit(gesture)
                self.last_gesture = gesture
                self.gesture_cooldown = 25  # Reduzido para 0.8s
            
            if not gesture:
                self.last_gesture = None
            
            if self.gesture_cooldown > 0:
                self.gesture_cooldown -= 1
            
            pixmap = self.convert_cv_to_pixmap(processed_frame)
            self.frame_ready.emit(pixmap)
            
            self.frame_count += 1
            
        cap.release()
    
    def process_frame(self, frame):
        """Processa frame"""
        h, w = frame.shape[:2]
        canvas = np.zeros((h, w, 3), dtype=np.uint8)
        canvas[:] = self.COLORS['background']
        
        # ROI maior e mais centralizado
        roi_x, roi_y = int(w * 0.35), int(h * 0.10)
        roi_w, roi_h = int(w * 0.60), int(h * 0.70)
        
        cv2.rectangle(canvas, (roi_x, roi_y), (roi_x + roi_w, roi_y + roi_h),
                     self.COLORS['primary'], 2, cv2.LINE_AA)
        cv2.putText(canvas, "ZONA GESTOS", (roi_x + 10, roi_y - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.COLORS['text'], 2, cv2.LINE_AA)
        
        roi = frame[roi_y:roi_y+roi_h, roi_x:roi_x+roi_w]
        
        # Equalização adaptativa para melhorar contraste
        roi_yuv = cv2.cvtColor(roi, cv2.COLOR_BGR2YUV)
        roi_yuv[:,:,0] = cv2.equalizeHist(roi_yuv[:,:,0])
        roi = cv2.cvtColor(roi_yuv, cv2.COLOR_YUV2BGR)
        
        # Detectar brilho médio para ajuste adaptativo
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        self.brightness_avg = np.mean(gray)
        
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        
        # Duplo filtro HSV (combina dois ranges)
        mask1 = cv2.inRange(hsv, self.lower_skin_1, self.upper_skin_1)
        mask2 = cv2.inRange(hsv, self.lower_skin_2, self.upper_skin_2)
        mask = cv2.bitwise_or(mask1, mask2)
        
        # Morphologia adaptativa (kernel maior em low-light)
        kernel_size = 9 if self.brightness_avg < 100 else 7
        kernel = np.ones((kernel_size, kernel_size), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=3)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=2)
        mask = cv2.medianBlur(mask, 7)  # Mediana melhor que Gaussiano
        mask = cv2.GaussianBlur(mask, (5, 5), 0)
        
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        gesture = None
        
        if contours:
            max_contour = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(max_contour)
            perimeter = cv2.arcLength(max_contour, True)
            
            # Threshold adaptativo baseado em iluminação
            min_area = 6000 if self.brightness_avg > 120 else 7500
            
            # Validar forma (perímetro vs área)
            if area > min_area and perimeter > 200:
                contour_global = max_contour + np.array([roi_x, roi_y])
                cv2.drawContours(canvas, [contour_global], -1, self.COLORS['primary'], 2, cv2.LINE_AA)
                
                hull = cv2.convexHull(max_contour, returnPoints=False)
                
                if len(hull) > 3 and len(max_contour) > 3:
                    defects = cv2.convexityDefects(max_contour, hull)
                    
                    if defects is not None:
                        finger_count = 0
                        for i in range(defects.shape[0]):
                            s, e, f, d = defects[i, 0]
                            start = tuple(max_contour[s][0])
                            end = tuple(max_contour[e][0])
                            far = tuple(max_contour[f][0])
                            
                            a = np.linalg.norm(np.array(start) - np.array(far))
                            b = np.linalg.norm(np.array(end) - np.array(far))
                            c = np.linalg.norm(np.array(start) - np.array(end))
                            
                            # Evitar divisão por zero
                            if a * b == 0:
                                continue
                            
                            angle = np.arccos(np.clip((a**2 + b**2 - c**2) / (2 * a * b), -1.0, 1.0)) * 180 / np.pi
                            
                            # Threshold adaptativo: mais permissivo em low-light
                            depth_threshold = 12000 if self.brightness_avg < 100 else 14000
                            
                            if angle <= 95 and d > depth_threshold:  # Ângulo mais permissivo
                                finger_count += 1
                                far_global = (far[0] + roi_x, far[1] + roi_y)
                                cv2.circle(canvas, far_global, 10, self.COLORS['secondary'], -1, cv2.LINE_AA)
                                cv2.circle(canvas, far_global, 14, self.COLORS['secondary'], 2, cv2.LINE_AA)
                        
                        gesture_text = None
                        if finger_count == 0:
                            gesture = "FIST"
                            gesture_text = "PUNHO"
                            self.gesture_confidence = 0.9
                        elif finger_count == 1:
                            gesture = "ONE"
                            gesture_text = "1 DEDO"
                            self.gesture_confidence = 0.85
                        elif finger_count == 2:
                            gesture = "TWO"
                            gesture_text = "2 DEDOS"
                            self.gesture_confidence = 0.8
                        elif finger_count == 3:
                            gesture = "THREE"
                            gesture_text = "3 DEDOS"
                            self.gesture_confidence = 0.75
                        elif finger_count >= 4:
                            gesture = "OPEN"
                            gesture_text = "MAO ABERTA"
                            self.gesture_confidence = 0.9
                        
                        if gesture_text:
                            cv2.putText(canvas, gesture_text, (31, h - 49),
                                       cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 4, cv2.LINE_AA)
                            cv2.putText(canvas, gesture_text, (30, h - 50),
                                       cv2.FONT_HERSHEY_SIMPLEX, 1.2, self.COLORS['text'], 3, cv2.LINE_AA)
                            
                            bar_w = int(200 * self.gesture_confidence)
                            cv2.rectangle(canvas, (30, h - 30), (30 + bar_w, h - 20),
                                        self.COLORS['primary'], -1)
                            cv2.rectangle(canvas, (30, h - 30), (230, h - 20),
                                        self.COLORS['primary'], 2)
                            
                            pulse = int(abs(np.sin(self.frame_count * 0.2)) * 30)
                            cv2.circle(canvas, (50, h - 100), 20 + pulse, self.COLORS['primary'], -1, cv2.LINE_AA)
                
                M = cv2.moments(max_contour)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"]) + roi_x
                    cy = int(M["m01"] / M["m00"]) + roi_y
                    cv2.circle(canvas, (cx, cy), 10, self.COLORS['primary'], -1, cv2.LINE_AA)
                    cv2.circle(canvas, (cx, cy), 15, self.COLORS['primary'], 2, cv2.LINE_AA)
        else:
            cv2.putText(canvas, "NENHUMA MAO", (w//2 - 80, h//2),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, self.COLORS['secondary'], 2, cv2.LINE_AA)
        
        # Grid
        for x in range(0, w, 50):
            cv2.line(canvas, (x, 0), (x, h), (0, 30, 60), 1, cv2.LINE_AA)
        for y in range(0, h, 50):
            cv2.line(canvas, (0, y), (w, y), (0, 30, 60), 1, cv2.LINE_AA)
        
        status = "ATIVO" if gesture else "AGUARDANDO"
        cv2.putText(canvas, f"STATUS: {status}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.COLORS['text'], 2, cv2.LINE_AA)
        
        # Info de brilho e consistência
        brightness_status = "BOA" if self.brightness_avg > 100 else "BAIXA"
        cv2.putText(canvas, f"LUZ: {brightness_status} ({int(self.brightness_avg)})", (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.COLORS['secondary'], 2, cv2.LINE_AA)
        
        # Mostrar histórico de gestos
        history_text = "|".join([g[:3] if g else "___" for g in self.gesture_history[-3:]])
        cv2.putText(canvas, f"HIST: [{history_text}]", (10, 90),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.COLORS['secondary'], 1, cv2.LINE_AA)
        
        return canvas, gesture
    
    def convert_cv_to_pixmap(self, cv_image):
        height, width, channel = cv_image.shape
        bytes_per_line = 3 * width
        q_image = QImage(cv_image.data, width, height, bytes_per_line,
                        QImage.Format.Format_BGR888)
        return QPixmap.fromImage(q_image)
    
    def stop(self):
        self.running = False
        self.wait()
