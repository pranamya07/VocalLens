# agents/vision_agent.py
"""
Vision Agent - Analyzes images to detect faces, objects, scenes, emotions
"""

import cv2
import numpy as np
import os
import json
from datetime import datetime

class VisionAgent:
    """
    Complete image understanding agent
    Detects faces, objects, scenes, emotions, and events
    """
    
    def __init__(self):
        # Load pre-trained classifiers (using OpenCV's built-in)
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        self.eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_eye.xml'
        )
        self.smile_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_smile.xml'
        )
        
        # Check if classifiers loaded properly
        if self.face_cascade.empty():
            print("⚠️ Warning: Face cascade not loaded properly")
        
        # Event visual knowledge
        self.event_visual_knowledge = {
            'wedding': {
                'colors': [(255,255,255), (0,0,0)],  # White, black
                'objects': ['rings', 'flowers', 'cake'],
                'patterns': ['group_photos', 'ceremony'],
                'detection': self._detect_wedding
            },
            'birthday': {
                'colors': [(255,192,203), (255,215,0)],  # Pink, gold
                'objects': ['cake', 'balloons', 'gifts'],
                'patterns': ['cake_cutting', 'party_hats'],
                'detection': self._detect_birthday
            },
            'beach': {
                'colors': [(135,206,235), (255,255,224)],  # Sky blue, sand
                'objects': ['water', 'sand', 'waves'],
                'patterns': ['swimsuits', 'sunset'],
                'detection': self._detect_beach
            }
        }
    
    def analyze_image(self, image_path):
        """
        Complete analysis of a single image
        """
        img = cv2.imread(image_path)
        if img is None:
            return None
        
        results = {
            'faces': self._detect_faces(img),
            'objects': self._detect_objects(img),
            'scene': self._classify_scene(img),
            'colors': self._extract_dominant_colors(img),
            'quality': self._assess_quality(img),
            'event': self._detect_event(img),
            'emotions': self._detect_emotions(img),
            'timestamp': datetime.now().isoformat()
        }
        
        # Generate tags from all analyses
        results['tags'] = self._generate_tags(results)
        
        return results
    
    def _detect_faces(self, img):
        """Detect faces using Haar cascades"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )
        
        face_results = []
        for (x, y, w, h) in faces:
            # Extract face ROI
            face_roi = gray[y:y+h, x:x+w]
            
            # Detect eyes (for confidence)
            eyes = self.eye_cascade.detectMultiScale(face_roi)
            
            # Detect smile
            smile = self.smile_cascade.detectMultiScale(face_roi, scaleFactor=1.7, minNeighbors=20)
            
            # Generate a unique face ID for this detection
            face_id = f"face_{x}_{y}_{w}_{h}".replace('-', '_')
            
            face_results.append({
                'face_id': face_id,
                'bbox': [int(x), int(y), int(w), int(h)],
                'confidence': min(1.0, len(eyes) * 0.5 + 0.3),
                'has_smile': len(smile) > 0,
                'eye_count': len(eyes),
                'person_id': None,  # Will be filled by memory agent when identified
                'relation': None    # Will be filled when user identifies
            })
        
        return face_results
    
    def _detect_objects(self, img):
        """
        Simple object detection using color segmentation
        """
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        objects = []
        
        # Detect sky/water (blue)
        blue_mask = cv2.inRange(hsv, np.array([90, 50, 50]), np.array([130, 255, 255]))
        blue_ratio = np.sum(blue_mask > 0) / blue_mask.size if blue_mask.size > 0 else 0
        if blue_ratio > 0.2:
            objects.append({'label': 'sky/water', 'confidence': float(blue_ratio)})
        
        # Detect vegetation (green)
        green_mask = cv2.inRange(hsv, np.array([40, 40, 40]), np.array([80, 255, 255]))
        green_ratio = np.sum(green_mask > 0) / green_mask.size if green_mask.size > 0 else 0
        if green_ratio > 0.2:
            objects.append({'label': 'vegetation', 'confidence': float(green_ratio)})
        
        # Detect sand/beige
        sand_mask = cv2.inRange(hsv, np.array([10, 20, 100]), np.array([30, 255, 255]))
        sand_ratio = np.sum(sand_mask > 0) / sand_mask.size if sand_mask.size > 0 else 0
        if sand_ratio > 0.15:
            objects.append({'label': 'sand', 'confidence': float(sand_ratio)})
        
        # Detect skin/people (if no faces detected separately)
        skin_mask = cv2.inRange(hsv, np.array([0, 20, 70]), np.array([20, 255, 255]))
        skin_ratio = np.sum(skin_mask > 0) / skin_mask.size if skin_mask.size > 0 else 0
        if skin_ratio > 0.1:
            objects.append({'label': 'people', 'confidence': float(skin_ratio)})
        
        return objects
    
    def _classify_scene(self, img):
        """
        Classify scene type (beach, city, indoor, etc.)
        """
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Calculate color ratios
        total_pixels = img.shape[0] * img.shape[1]
        
        blue_ratio = np.sum(cv2.inRange(hsv, [90,50,50], [130,255,255]) > 0) / total_pixels
        green_ratio = np.sum(cv2.inRange(hsv, [40,40,40], [80,255,255]) > 0) / total_pixels
        sand_ratio = np.sum(cv2.inRange(hsv, [10,20,100], [30,255,255]) > 0) / total_pixels
        
        # Edge detection for city scenes
        edges = cv2.Canny(gray, 50, 150)
        edge_ratio = np.sum(edges > 0) / edges.size if edges.size > 0 else 0
        
        # Variance for indoor detection
        variance = np.var(gray)
        
        # Classify
        if blue_ratio > 0.3 and sand_ratio > 0.15:
            return {'type': 'beach', 'confidence': 0.8}
        elif green_ratio > 0.4:
            return {'type': 'nature', 'confidence': 0.7}
        elif edge_ratio > 0.2:
            return {'type': 'city', 'confidence': 0.7}
        elif variance < 2000:
            return {'type': 'indoor', 'confidence': 0.6}
        else:
            return {'type': 'outdoor', 'confidence': 0.5}
    
    def _detect_event(self, img):
        """
        Detect if image is from a specific event type
        """
        # Check for wedding
        wedding_score = self._detect_wedding(img)
        if wedding_score > 0.5:
            return {'type': 'wedding', 'confidence': float(wedding_score)}
        
        # Check for birthday
        birthday_score = self._detect_birthday(img)
        if birthday_score > 0.5:
            return {'type': 'birthday', 'confidence': float(birthday_score)}
        
        # Check for beach
        beach_score = self._detect_beach(img)
        if beach_score > 0.5:
            return {'type': 'beach', 'confidence': float(beach_score)}
        
        return {'type': 'unknown', 'confidence': 0.0}
    
    def _detect_wedding(self, img):
        """Detect if this is a wedding photo"""
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # Look for white (wedding dress)
        white_mask = cv2.inRange(hsv, np.array([0, 0, 200]), np.array([180, 30, 255]))
        white_ratio = np.sum(white_mask > 0) / white_mask.size if white_mask.size > 0 else 0
        
        # Look for formal wear (dark colors)
        dark_mask = cv2.inRange(hsv, np.array([0, 0, 0]), np.array([180, 255, 50]))
        dark_ratio = np.sum(dark_mask > 0) / dark_mask.size if dark_mask.size > 0 else 0
        
        # Check for group photo (many faces)
        faces = self._detect_faces(img)
        
        score = 0.0
        if white_ratio > 0.1:
            score += 0.3
        if dark_ratio > 0.1:
            score += 0.2
        if len(faces) > 3:
            score += 0.3
        
        return min(score, 1.0)
    
    def _detect_birthday(self, img):
        """Detect if this is a birthday photo"""
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # Look for bright colors (balloons, decorations)
        bright_mask = cv2.inRange(hsv, np.array([0, 100, 100]), np.array([180, 255, 255]))
        bright_ratio = np.sum(bright_mask > 0) / bright_mask.size if bright_mask.size > 0 else 0
        
        # Look for cake (brown + white)
        brown_mask = cv2.inRange(hsv, np.array([10, 100, 100]), np.array([20, 255, 200]))
        white_mask = cv2.inRange(hsv, np.array([0, 0, 200]), np.array([180, 30, 255]))
        
        score = 0.0
        if bright_ratio > 0.2:
            score += 0.3
        if np.sum(brown_mask) > 5000 and np.sum(white_mask) > 5000:
            score += 0.4
        
        return min(score, 1.0)
    
    def _detect_beach(self, img):
        """Detect if this is a beach photo"""
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        blue_ratio = np.sum(cv2.inRange(hsv, [90,50,50], [130,255,255]) > 0) / (img.shape[0] * img.shape[1])
        sand_ratio = np.sum(cv2.inRange(hsv, [10,20,100], [30,255,255]) > 0) / (img.shape[0] * img.shape[1])
        
        return min(float(blue_ratio + sand_ratio), 1.0)
    
    def _detect_emotions(self, img):
        """
        Simple emotion detection based on facial features
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
        
        emotions = []
        for (x, y, w, h) in faces:
            face_roi = gray[y:y+h, x:x+w]
            
            # Simple smile detection
            smile = self.smile_cascade.detectMultiScale(face_roi, 1.7, 20)
            
            if len(smile) > 0:
                emotions.append({'type': 'happy', 'confidence': 0.7})
            else:
                emotions.append({'type': 'neutral', 'confidence': 0.5})
        
        return emotions
    
    def _extract_dominant_colors(self, img, k=3):
        """
        Extract dominant colors using k-means
        """
        pixels = img.reshape(-1, 3).astype(np.float32)
        
        # Simple k-means implementation
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
        _, labels, centers = cv2.kmeans(pixels, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
        
        # Count pixels per cluster
        counts = np.bincount(labels.flatten())
        
        colors = []
        for i in range(k):
            colors.append({
                'rgb': centers[i].tolist(),
                'percentage': float(counts[i] / len(labels)) if len(labels) > 0 else 0
            })
        
        return sorted(colors, key=lambda x: x['percentage'], reverse=True)
    
    def _assess_quality(self, img):
        """
        Assess image quality (sharpness, brightness, contrast)
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Sharpness (variance of Laplacian)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        sharpness = np.var(laplacian)
        
        # Brightness
        brightness = np.mean(gray)
        
        # Contrast
        contrast = np.std(gray)
        
        # Normalize scores
        quality = {
            'sharpness': min(sharpness / 500, 1.0) if sharpness > 0 else 0,
            'brightness': min(brightness / 200, 1.0) if brightness < 200 else max(0, 1 - (brightness - 200) / 100),
            'contrast': min(contrast / 70, 1.0) if contrast > 0 else 0,
            'overall': 0.0
        }
        
        quality['overall'] = (quality['sharpness'] * 0.4 + 
                             quality['brightness'] * 0.3 + 
                             quality['contrast'] * 0.3)
        
        return quality
    
    def _generate_tags(self, analysis):
        """
        Generate tags from all analyses
        """
        tags = []
        
        # Add scene tag
        if 'scene' in analysis and analysis['scene']:
            tags.append(analysis['scene']['type'])
        
        # Add event tag
        if 'event' in analysis and analysis['event']['confidence'] > 0.5:
            tags.append(analysis['event']['type'])
        
        # Add object tags
        for obj in analysis.get('objects', []):
            tags.append(obj['label'])
        
        # Add face-related tags
        faces = analysis.get('faces', [])
        if faces:
            tags.append('has_people')
            if len(faces) > 1:
                tags.append('group_photo')
            if any(face.get('has_smile') for face in faces):
                tags.append('happy')
        
        # Add emotion tags
        for emotion in analysis.get('emotions', []):
            tags.append(emotion['type'])
        
        return list(set(tags))  # Remove duplicates