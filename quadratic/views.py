from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import math
import io
import base64
import re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from django.shortcuts import render
from django.conf import settings
import hashlib
import time
import json

def landing_page(request):
    return render(request, 'quadratic/landing_page.html')

def index(request):
    return render(request, 'quadratic/index.html')

def parse_quadratic_expression(expression):
    """
    Parse berbagai format input fungsi kuadrat
    Mendukung format:
    - f(x) = ax² + bx + c
    - y = ax² + bx + c
    - ax² + bx + c
    - a(x+h)² + k (bentuk vertex)
    - a(x-h)² + k (bentuk vertex)
    """
    # Bersihkan spasi dan lowercase
    expr = expression.replace(' ', '').lower()
    
    # Hilangkan f(x)= atau y=
    expr = re.sub(r'^(f\(x\)|y)=', '', expr)
    
    # Ganti x² atau x^2 dengan standar format
    expr = expr.replace('²', '^2')
    expr = expr.replace('x2', 'x^2')
    
    # Deteksi bentuk vertex: a(x+h)² + k atau a(x-h)² + k
    # Pattern yang lebih fleksibel untuk menangani berbagai format
    vertex_patterns = [
        r'([+-]?\d*\.?\d*)\(x([+-]\d+\.?\d*)\)\^2([+-]?\d+\.?\d*)',  # a(x+h)^2+k
        r'([+-]?\d*\.?\d*)\(x([+-]\d+\.?\d*)\)\^2$',  # a(x+h)^2 tanpa k
    ]
    
    for pattern in vertex_patterns:
        vertex_match = re.search(pattern, expr)
        if vertex_match:
            # Parse bentuk vertex
            a_str = vertex_match.group(1)
            h_str = vertex_match.group(2)
            k_str = vertex_match.group(3) if len(vertex_match.groups()) >= 3 else '0'
            
            # Handle koefisien a
            if a_str == '' or a_str == '+':
                a = 1.0
            elif a_str == '-':
                a = -1.0
            else:
                a = float(a_str) if a_str else 1.0
            
            # Handle h (sudah dengan tanda dari input)
            h = float(h_str)
            
            # Handle k
            if k_str == '' or k_str == '+':
                k = 0.0
            else:
                k = float(k_str) if k_str else 0.0
            
            # Konversi ke bentuk standar: a(x-h)² + k → ax² + bx + c
            # Jika input (x+1) maka h = 1, tapi rumus vertex form adalah (x-h)²
            # Jadi kita perlu balik tanda: (x+1)² = (x-(-1))²
            h_vertex = -h  # Balik tanda untuk konversi ke bentuk standar
            
            # a(x-h)² + k = a(x² - 2hx + h²) + k = ax² - 2ahx + ah² + k
            a_coef = a
            b_coef = -2 * a * h_vertex
            c_coef = a * h_vertex * h_vertex + k
            
            return a_coef, b_coef, c_coef
    
    # Parse bentuk standar
    # Pattern untuk ax^2
    a_pattern = r'([+-]?\d*\.?\d*)x\^2'
    a_match = re.search(a_pattern, expr)
    
    # Pattern untuk bx (tidak diikuti ^)
    b_pattern = r'([+-]?\d*\.?\d*)x(?!\^)'
    b_match = re.search(b_pattern, expr)
    
    # Extract koefisien a
    if a_match:
        a_str = a_match.group(1)
        if a_str == '' or a_str == '+':
            a = 1.0
        elif a_str == '-':
            a = -1.0
        else:
            a = float(a_str)
    else:
        a = 0.0
    
    # Extract koefisien b
    if b_match:
        b_str = b_match.group(1)
        if b_str == '' or b_str == '+':
            b = 1.0
        elif b_str == '-':
            b = -1.0
        else:
            b = float(b_str)
    else:
        b = 0.0
    
    # Extract konstanta c - cari angka yang tidak diikuti x atau ^
    c = 0.0
    c_pattern = r'([+-]?\d+\.?\d*)(?![x\^])'
    c_matches = re.findall(c_pattern, expr)
    
    for match in c_matches:
        if match and match not in ['', '+', '-']:
            # Cek apakah angka ini bagian dari koefisien lain
            pos = expr.find(match)
            if pos > 0:
                # Cek karakter sebelum dan sesudah
                if pos + len(match) < len(expr):
                    next_char = expr[pos + len(match)]
                    if next_char not in ['x', '^']:
                        c = float(match)
                        break
                else:
                    c = float(match)
                    break
            elif pos == 0 and not expr[len(match):].startswith('x'):
                c = float(match)
                break
    
    return a, b, c

def calculate(request):
    """
    Endpoint untuk kalkulasi dan visualisasi fungsi kuadrat
    """
    if request.method == 'POST':
        try:
            mode = request.POST.get('mode', 'y')
            
            if mode == 'freetext':
                expression = request.POST.get('expression', '')
                if not expression:
                    return JsonResponse({
                        'success': False,
                        'error': 'Masukkan persamaan fungsi kuadrat'
                    })
                
                a, b, c = parse_quadratic_expression(expression)
                
            else:
                a = float(request.POST.get('a', 0))
                b = float(request.POST.get('b', 0))
                c = float(request.POST.get('c', 0))
            
            # Validasi: a tidak boleh 0
            if a == 0:
                return JsonResponse({
                    'success': False,
                    'error': 'Koefisien a tidak boleh 0 (bukan fungsi kuadrat)'
                })
            
            # Generate grafik dan analisis
            if mode == 'x':
                result = calculate_x_mode(a, b, c)
            else:
                result = calculate_y_mode(a, b, c)
            
            return JsonResponse(result)
            
        except ValueError as e:
            return JsonResponse({
                'success': False,
                'error': f'Input tidak valid: {str(e)}'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Terjadi kesalahan: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'error': 'Method tidak valid'
    })

def calculate_y_mode(a, b, c):
    """
    Kalkulasi untuk mode Y: y = ax² + bx + c
    """
    # 1. ARAH BUKA PARABOLA
    arah = "ke atas ⬆️" if a > 0 else "ke bawah ⬇️"
    
    # 2. TITIK PUNCAK
    x_puncak = -b / (2 * a)
    y_puncak = a * (x_puncak ** 2) + b * x_puncak + c
    titik_puncak = f"({x_puncak:.2f}, {y_puncak:.2f})"
    
    # Rumus titik puncak
    rumus_puncak = {
        'xp': f"xₚ = -b/(2a) = -({b})/(2×{a}) = {x_puncak:.2f}",
        'yp': f"yₚ = a(xₚ)² + b(xₚ) + c = {a}({x_puncak:.2f})² + {b}({x_puncak:.2f}) + {c} = {y_puncak:.2f}"
    }
    
    # 3. SUMBU SIMETRI
    sumbu_simetri = f"x = {x_puncak:.2f}"
    
    # 4. TITIK POTONG SUMBU Y
    y_intercept = c
    titik_potong_y = f"(0, {y_intercept:.2f})"
    rumus_potong_y = f"Substitusi x = 0 → y = {a}(0)² + {b}(0) + {c} = {c}"
    
    # 5. TITIK POTONG SUMBU X
    discriminant = b**2 - 4*a*c
    rumus_diskriminan = f"D = b² - 4ac = ({b})² - 4({a})({c}) = {discriminant:.2f}"
    
    if discriminant > 0:
        x1 = (-b + math.sqrt(discriminant)) / (2 * a)
        x2 = (-b - math.sqrt(discriminant)) / (2 * a)
        titik_potong_x = f"({x1:.2f}, 0) dan ({x2:.2f}, 0)"
        x_roots = [x1, x2]
        rumus_potong_x = f"x₁,₂ = (-b ± √D)/(2a) = (-({b}) ± √{discriminant:.2f})/(2×{a})\nx₁ = {x1:.2f}, x₂ = {x2:.2f}"
    elif discriminant == 0:
        x1 = -b / (2 * a)
        titik_potong_x = f"({x1:.2f}, 0)"
        x_roots = [x1]
        rumus_potong_x = f"x = -b/(2a) = -({b})/(2×{a}) = {x1:.2f}"
    else:
        titik_potong_x = "Tidak memotong sumbu X"
        x_roots = []
        rumus_potong_x = f"D < 0, maka tidak ada akar real (parabola tidak memotong sumbu X)"
    
    # GENERATE GRAFIK
    plt.figure(figsize=(8, 6))
    
    # Tentukan range x untuk plotting yang lebih baik
    if x_roots:
        x_min = min(x_roots + [x_puncak]) - 3
        x_max = max(x_roots + [x_puncak]) + 3
    else:
        x_min = x_puncak - 5
        x_max = x_puncak + 5
    
    # Adjust range untuk y
    x = np.linspace(x_min, x_max, 500)
    y = a * x**2 + b * x + c
    
    # Plot parabola
    plt.plot(x, y, 'b-', linewidth=2.5, label=format_equation(a, b, c, 'y'))
    
    # Plot titik puncak
    plt.plot(x_puncak, y_puncak, 'ro', markersize=10, label=f'Puncak {titik_puncak}', zorder=5)
    
    # Plot titik potong Y
    plt.plot(0, y_intercept, 'go', markersize=8, label=f'Potong Y {titik_potong_y}', zorder=5)
    
    # Plot titik potong X (jika ada)
    if x_roots:
        for i, x_root in enumerate(x_roots):
            plt.plot(x_root, 0, 'mo', markersize=8, 
                    label=f'Potong X ({x_root:.2f}, 0)' if i == 0 else '', zorder=5)
    
    # Plot sumbu simetri
    y_min_plot, y_max_plot = plt.ylim()
    plt.axvline(x=x_puncak, color='r', linestyle='--', linewidth=1.5, 
                alpha=0.5, label=f'Sumbu Simetri: x={x_puncak:.2f}')
    
    # Grid dan styling
    plt.grid(True, alpha=0.3, linestyle='--', linewidth=0.8)
    plt.axhline(y=0, color='k', linewidth=1.2)
    plt.axvline(x=0, color='k', linewidth=1.2)
    plt.xlabel('x', fontsize=12, fontweight='bold')
    plt.ylabel('y', fontsize=12, fontweight='bold')
    plt.title(format_equation(a, b, c, 'y'), fontsize=13, fontweight='bold', pad=15)
    plt.legend(loc='best', fontsize=9, framealpha=0.9)
    
    # Simpan grafik
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight', facecolor='white')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
    plt.close()
    
    return {
        'success': True,
        'mode': 'y',
        'persamaan': format_equation(a, b, c, 'y'),
        'arah_parabola': arah,
        'titik_puncak': titik_puncak,
        'rumus_puncak': rumus_puncak,
        'sumbu_simetri': sumbu_simetri,
        'titik_potong_y': titik_potong_y,
        'rumus_potong_y': rumus_potong_y,
        'titik_potong_x': titik_potong_x,
        'rumus_potong_x': rumus_potong_x,
        'discriminant': round(discriminant, 2),
        'rumus_diskriminan': rumus_diskriminan,
        'grafik': image_base64
    }

def calculate_x_mode(a, b, c):
    """
    Kalkulasi untuk mode X: x = ay² + by + c
    """
    # 1. ARAH BUKA PARABOLA
    arah = "ke kanan ➡️" if a > 0 else "ke kiri ⬅️"
    
    # 2. TITIK PUNCAK
    y_puncak = -b / (2 * a)
    x_puncak = a * (y_puncak ** 2) + b * y_puncak + c
    titik_puncak = f"({x_puncak:.2f}, {y_puncak:.2f})"
    
    rumus_puncak = {
        'yp': f"yₚ = -b/(2a) = -({b})/(2×{a}) = {y_puncak:.2f}",
        'xp': f"xₚ = a(yₚ)² + b(yₚ) + c = {a}({y_puncak:.2f})² + {b}({y_puncak:.2f}) + {c} = {x_puncak:.2f}"
    }
    
    # 3. SUMBU SIMETRI
    sumbu_simetri = f"y = {y_puncak:.2f}"
    
    # 4. TITIK POTONG SUMBU X
    x_intercept = c
    titik_potong_x = f"({x_intercept:.2f}, 0)"
    rumus_potong_x = f"Substitusi y = 0 → x = {a}(0)² + {b}(0) + {c} = {c}"
    
    # 5. TITIK POTONG SUMBU Y
    discriminant = b**2 - 4*a*c
    rumus_diskriminan = f"D = b² - 4ac = ({b})² - 4({a})({c}) = {discriminant:.2f}"
    
    if discriminant > 0:
        y1 = (-b + math.sqrt(discriminant)) / (2 * a)
        y2 = (-b - math.sqrt(discriminant)) / (2 * a)
        titik_potong_y = f"(0, {y1:.2f}) dan (0, {y2:.2f})"
        y_roots = [y1, y2]
        rumus_potong_y = f"y₁,₂ = (-b ± √D)/(2a) = (-({b}) ± √{discriminant:.2f})/(2×{a})\ny₁ = {y1:.2f}, y₂ = {y2:.2f}"
    elif discriminant == 0:
        y1 = -b / (2 * a)
        titik_potong_y = f"(0, {y1:.2f})"
        y_roots = [y1]
        rumus_potong_y = f"y = -b/(2a) = -({b})/(2×{a}) = {y1:.2f}"
    else:
        titik_potong_y = "Tidak memotong sumbu Y"
        y_roots = []
        rumus_potong_y = f"D < 0, maka tidak ada akar real (parabola tidak memotong sumbu Y)"
    
    # GENERATE GRAFIK
    plt.figure(figsize=(8, 6))
    
    if y_roots:
        y_min = min(y_roots + [y_puncak]) - 3
        y_max = max(y_roots + [y_puncak]) + 3
    else:
        y_min = y_puncak - 5
        y_max = y_puncak + 5
    
    y = np.linspace(y_min, y_max, 500)
    x = a * y**2 + b * y + c
    
    plt.plot(x, y, 'b-', linewidth=2.5, label=format_equation(a, b, c, 'x'))
    plt.plot(x_puncak, y_puncak, 'ro', markersize=10, label=f'Puncak {titik_puncak}', zorder=5)
    plt.plot(x_intercept, 0, 'go', markersize=8, label=f'Potong X {titik_potong_x}', zorder=5)
    
    if y_roots:
        for i, y_root in enumerate(y_roots):
            plt.plot(0, y_root, 'mo', markersize=8,
                    label=f'Potong Y (0, {y_root:.2f})' if i == 0 else '', zorder=5)
    
    x_min_plot, x_max_plot = plt.xlim()
    plt.axhline(y=y_puncak, color='r', linestyle='--', linewidth=1.5,
                alpha=0.5, label=f'Sumbu Simetri: y={y_puncak:.2f}')
    
    plt.grid(True, alpha=0.3, linestyle='--', linewidth=0.8)
    plt.axhline(y=0, color='k', linewidth=1.2)
    plt.axvline(x=0, color='k', linewidth=1.2)
    plt.xlabel('x', fontsize=12, fontweight='bold')
    plt.ylabel('y', fontsize=12, fontweight='bold')
    plt.title(format_equation(a, b, c, 'x'), fontsize=13, fontweight='bold', pad=15)
    plt.legend(loc='best', fontsize=9, framealpha=0.9)
    
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight', facecolor='white')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
    plt.close()
    
    return {
        'success': True,
        'mode': 'x',
        'persamaan': format_equation(a, b, c, 'x'),
        'arah_parabola': arah,
        'titik_puncak': titik_puncak,
        'rumus_puncak': rumus_puncak,
        'sumbu_simetri': sumbu_simetri,
        'titik_potong_x': titik_potong_x,
        'rumus_potong_x': rumus_potong_x,
        'titik_potong_y': titik_potong_y,
        'rumus_potong_y': rumus_potong_y,
        'discriminant': round(discriminant, 2),
        'rumus_diskriminan': rumus_diskriminan,
        'grafik': image_base64
    }

def format_equation(a, b, c, var='y'):
    """
    Format persamaan dengan tanda yang benar
    """
    if a == 1:
        a_str = ""
    elif a == -1:
        a_str = "-"
    else:
        a_str = str(a)
    
    if b == 0:
        b_str = ""
    elif b > 0:
        if b == 1:
            b_str = f" + {var}"
        else:
            b_str = f" + {b}{var}"
    else:
        if b == -1:
            b_str = f" - {var}"
        else:
            b_str = f" - {abs(b)}{var}"
    
    if c == 0:
        c_str = ""
    elif c > 0:
        c_str = f" + {c}"
    else:
        c_str = f" - {abs(c)}"
    
    if var == 'y':
        result = f"y = {a_str}x²{b_str}{c_str}"
    else:
        result = f"x = {a_str}y²{b_str}{c_str}"
    
    return result.replace("  ", " ").strip()

@csrf_exempt
@require_http_methods(["POST"])
def send_contact_email(request):
    try:
        data = json.loads(request.body)
        
        user_email = data.get('user_email', '').strip().lower()
        user_name = data.get('user_name', '').strip()
        subject = data.get('subject', '').strip()
        message = data.get('message', '').strip()
        
        # Validasi input
        if not all([user_email, user_name, subject, message]):
            return JsonResponse({
                'success': False,
                'error': 'Semua field harus diisi'
            }, status=400)
        
        # Validasi email domain UPI
        if not (user_email.endswith('@upi.edu') or user_email.endswith('@student.upi.edu')):
            return JsonResponse({
                'success': False,
                'error': 'Hanya email dengan domain UPI yang diperbolehkan'
            }, status=400)
        
        # Validasi credentials EmailJS tersedia
        if not all([settings.EMAILJS_PUBLIC_KEY, settings.EMAILJS_SERVICE_ID, settings.EMAILJS_TEMPLATE_ID]):
            return JsonResponse({
                'success': False,
                'error': 'Konfigurasi email belum lengkap. Silakan hubungi administrator.'
            }, status=500)
        
        # Return credentials langsung tanpa rate limiting
        return JsonResponse({
            'success': True,
            'credentials': {
                'public_key': settings.EMAILJS_PUBLIC_KEY,
                'service_id': settings.EMAILJS_SERVICE_ID,
                'template_id': settings.EMAILJS_TEMPLATE_ID
            },
            'message': 'Silakan lanjutkan mengirim email'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Format data tidak valid'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Terjadi kesalahan: {str(e)}'
        }, status=500)