
import os
import glob

def hex_to_coe(input_path, output_path):
    if not os.path.exists(input_path):
        return

    with open(input_path, 'r') as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]

    if not lines:
        return

    target_len = len(lines[0])

    with open(output_path, 'w') as f:
        f.write("memory_initialization_radix=16;\n")
        f.write("memory_initialization_vector=\n")

        total_lines = len(lines)
        for i, line in enumerate(lines):
            if len(line) < target_len:
                line = line.ljust(target_len, '0')

            if i == total_lines - 1:
                f.write(f"{line};\n")
            else:
                f.write(f"{line},\n")

def combine_scales_and_biases_to_coe(scale_files, bias_files, output_path):
    all_lines = []

    # 1. Scale 처리 (4-bit 단위 할당)
    extracted_scales = []
    for file_path in sorted(scale_files):
        with open(file_path, 'r') as f:
            content = f.read().strip()
            if content:
                # 4-bit 데이터이므로 마스킹을 0xF로 적용
                val = int(content[0], 16) & 0xF
                extracted_scales.append(val)

    if extracted_scales:
        # 32-bit(8글자 Hex) 라인 하나에 4-bit 데이터 8개가 들어감
        for i in range(0, len(extracted_scales), 8):
            chunk = extracted_scales[i:i+8]
            line_val = 0
            for idx, val in enumerate(chunk):
                # 최상위 비트(MSB)부터 4비트씩 채워 넣음
                shift = 28 - (idx * 4)
                line_val |= (val & 0xF) << shift
            
            all_lines.append(f"{line_val:08X}")

    # 2. Bias 처리 및 패딩 적용 
    target_len = 8 # 기본값: scale과 동일하게 8자리(32-bit) 기준
    
    # Bias 파일 중 첫 번째 파일에서 한 줄의 길이를 알아내어 패딩 기준으로 삼음
    for file_path in sorted(bias_files):
        with open(file_path, 'r') as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
            if lines:
                target_len = len(lines[0])
                break

    # 정렬된 Bias 파일들을 순회하며 데이터 이어 붙이기
    for file_path in sorted(bias_files):
        with open(file_path, 'r') as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
            for line in lines:
                # 데이터를 왼쪽에 두고 우측 남는 공간을 0으로 채움 (좌측 정렬)
                padded_line = line.ljust(target_len, '0')
                all_lines.append(padded_line)

    # 3. COE 파일 작성
    if not all_lines:
        return

    with open(output_path, 'w') as f:
        f.write("memory_initialization_radix=16;\n")
        f.write("memory_initialization_vector=\n")

        total_lines = len(all_lines)
        for i, line in enumerate(all_lines):
            if i == total_lines - 1:
                f.write(f"{line};\n")
            else:
                f.write(f"{line},\n")

def make_padded_coe(file1, start1, file2, start2, file3, start3, output_path):
    files_info = [
        (file1, start1, True),  # True: 3개마다 패딩 적용
        (file2, start2, False), # False: 패딩 없음
        (file3, start3, False)  # False: 패딩 없음
    ]
    
    all_lines = []
    current_line = 0
    target_len = 0
    
    # 1. target_len 결정
    for file_path, _, _ in files_info:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                first = f.readline().strip()
                if first:
                    target_len = len(first)
                    break
    
    if target_len == 0: return
    padding_str = '0' * target_len

    # 2. 파일별 루프
    for file_path, start_line, apply_padding in files_info:
        if not os.path.exists(file_path): continue
            
        # 시작 지점 패딩
        if current_line < start_line:
            gap = start_line - current_line
            all_lines.extend([padding_str] * gap)
            current_line = start_line
            
        with open(file_path, 'r') as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
            
            for i, line in enumerate(lines):
                all_lines.append(line.ljust(target_len, '0'))
                current_line += 1
                
                # file1(apply_padding=True)인 경우에만 3개마다 패딩 추가
                if apply_padding and (i + 1) % 3 == 0:
                    all_lines.append(padding_str)
                    current_line += 1
                
    # 3. 파일 쓰기
    with open(output_path, 'w') as f:
        f.write("memory_initialization_radix=16;\n")
        f.write("memory_initialization_vector=\n")
        
        total = len(all_lines)
        for i, line in enumerate(all_lines):
            suffix = ";" if i == total - 1 else ","
            f.write(f"{line}{suffix}\n")

if __name__ == "__main__":
    feamap_dir = "../bin/log_feamap"
    params_dir = "../bin/log_param"
    output_dir = "../bin/log_coe"

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    all_hex_files = glob.glob(os.path.join(feamap_dir, "*.hex")) + glob.glob(os.path.join(params_dir, "*.hex"))
    
    # 파일 분류
    scale_files = [f for f in all_hex_files if "scales.hex" in f]
    bias_files = [f for f in all_hex_files if "biases.hex" in f] # bias 파일 필터링 추가
    
    # scale과 bias를 제외한 나머지 파일들
    other_hex_files = [f for f in all_hex_files if "scales.hex" not in f and "biases.hex" not in f]

    # 1. 나머지 일반 파일들은 개별 COE로 변환
    for hex_file in other_hex_files:
        base_name = os.path.basename(hex_file)
        file_name = os.path.splitext(base_name)[0]
        coe_file = os.path.join(output_dir, file_name + ".coe")
        hex_to_coe(hex_file, coe_file)

    # 2. Scale과 Bias 파일 하나로 통합
    combined_scales_biases_file = os.path.join(output_dir, "combined_scales_and_biases.coe")
    combine_scales_and_biases_to_coe(scale_files, bias_files, combined_scales_biases_file)

    # 3. Weight 패딩 처리
    make_padded_coe(
        file1="../bin/log_param/CONV00_param_weight.hex", start1=0,
        file2="../bin/log_param/CONV02_param_weight.hex", start2=512,
        file3="../bin/log_param/CONV04_param_weight.hex", start3=2048,
        output_path=os.path.join(output_dir, "combined_weights.coe")
    )