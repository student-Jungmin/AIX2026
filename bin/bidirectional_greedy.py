import subprocess
import re
import csv
import sys
import copy

# 1. Candidates
INPUT_CANDIDATES = [
    [64.0, 128.0, 256.0], # CONV 0
    [4.0, 8.0, 16.0],     # CONV 2
    [4.0, 8.0, 16.0],     # CONV 4
    [4.0, 8.0, 16.0],     # CONV 6
    [8.0, 16.0, 32.0],    # CONV 8
    [4.0, 8.0, 16.0],     # CONV 10
    [8.0, 16.0, 32.0],    # CONV 12
    [8.0, 16.0, 32.0],    # CONV 13
    [4.0, 8.0, 16.0],     # CONV 14
    [8.0, 16.0, 32.0],    # CONV 17
    [4.0, 8.0, 16.0]      # CONV 20
]

WEIGHT_CANDIDATES = [
    [8.0, 16.0, 32.0],        # CONV 0
    [128.0, 256.0, 512.0],    # CONV 2
    [128.0, 256.0, 512.0],    # CONV 4
    [128.0, 256.0, 512.0],    # CONV 6
    [128.0, 256.0, 512.0],    # CONV 8
    [512.0, 1024.0, 2048.0],  # CONV 10
    [256.0, 512.0, 1024.0],   # CONV 12
    [256.0, 512.0, 1024.0],   # CONV 13
    [128.0, 256.0, 512.0],    # CONV 14
    [64.0, 128.0, 256.0],     # CONV 17
    [128.0, 256.0, 512.0]     # CONV 20
]

# 2. Regular expression patterns for finding mAP in console
map_pattern = re.compile(r"mean average precision \(mAP\) = [\d\.]+, or ([\d\.]+) %")
time_pattern = re.compile(r"Total Detection Time: ([\d\.]+) Seconds")

# 3. Evaluation function
def evaluate_model(inputs, weights, run_id):
    with open("quant_multipliers.txt", "w") as f:
        for i in range(11):
            f.write(f"{inputs[i]} {weights[i]}\n")
            
    try:
        result = subprocess.run(
            ["bash", "./script-unix-aix2024-test-all-quantized.sh"], 
            capture_output=True, text=True, check=True
        )
        output = result.stdout
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Run {run_id} execution failed.")
        return 0.0, 0.0

    map_match = map_pattern.search(output)
    time_match = time_pattern.search(output)
    
    current_map = float(map_match.group(1)) if map_match else 0.0
    current_time = float(time_match.group(1)) if time_match else 0.0
    
    return current_map, current_time

# 4. One-directional greedy search 
def run_directional_search(direction="forward", start_run_id=1, writer=None, csvfile=None):
    # Initialize baseline near the best FP32 scales
    best_inputs = [cands[1] for cands in INPUT_CANDIDATES]
    best_weights = [cands[1] for cands in WEIGHT_CANDIDATES]
    
    layer_order = range(11) if direction == "forward" else reversed(range(11))
    
    print(f"[INFO] Starting {direction} search.")

    run_id = start_run_id
    direction_best_map = 0.0

    for layer_idx in layer_order:
        in_cands = INPUT_CANDIDATES[layer_idx]
        wt_cands = WEIGHT_CANDIDATES[layer_idx]
        
        print(f"[INFO] Optimizing Layer {layer_idx}...")
        layer_best_map = 0.0
        layer_best_in = best_inputs[layer_idx]
        layer_best_wt = best_weights[layer_idx]

        for i_val in in_cands:
            for w_val in wt_cands:
                current_inputs = copy.deepcopy(best_inputs)
                current_weights = copy.deepcopy(best_weights)
                
                current_inputs[layer_idx] = i_val
                current_weights[layer_idx] = w_val

                current_map, current_time = evaluate_model(current_inputs, current_weights, run_id)
                
                print(f"[DEBUG] Run {run_id:03d} | In: {i_val:<5} | Wt: {w_val:<6} | mAP: {current_map:.2f} %")

                if writer and csvfile:
                    writer.writerow([run_id, direction, f"Layer_{layer_idx}", current_map, current_time] + 
                                    current_inputs + current_weights)
                    csvfile.flush()

                if current_map > layer_best_map:
                    layer_best_map = current_map
                    layer_best_in = i_val
                    layer_best_wt = w_val

                run_id += 1

        # Decide scales in current layer
        best_inputs[layer_idx] = layer_best_in
        best_weights[layer_idx] = layer_best_wt
        
        print(f"[INFO] Layer {layer_idx} finalized. (In: {layer_best_in}, Wt: {layer_best_wt}, mAP: {layer_best_map:.2f} %)")
        
        if layer_best_map > direction_best_map:
            direction_best_map = layer_best_map

    return direction_best_map, best_inputs, best_weights, run_id

# 5. Bi-directional greedy search
def main():
    total_runs_per_direction = sum([len(INPUT_CANDIDATES[i]) * len(WEIGHT_CANDIDATES[i]) for i in range(11)])
    total_runs = total_runs_per_direction * 2
    
    print(f"[INFO] Starting Bi-directional Greedy Search.")
    print(f"[INFO] Estimated total runs: {total_runs}")
    print(f"[INFO] Estimated execution time: {total_runs * 58 / 60:.1f} minutes ({total_runs * 58 / 3600:.1f} hours)")

    with open('bidirectional_greedy_results.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Run_ID', 'Direction', 'Layer_Optimized', 'mAP(%)', 'Time(Sec)'] + 
                        [f'In_{i}' for i in range(11)] + [f'Wt_{i}' for i in range(11)])

        # 5-1. Forward search
        fw_map, fw_inputs, fw_weights, next_run_id = run_directional_search("forward", 1, writer, csvfile)
        
        # 5-2. Backward search
        bw_map, bw_inputs, bw_weights, _ = run_directional_search("backward", next_run_id, writer, csvfile)

    print("[INFO] Search complete. Comparing final results.")
    print(f"[INFO] Best forward mAP : {fw_map:.2f} %")
    print(f"[INFO] Best backward mAP: {bw_map:.2f} %")
    
    if fw_map >= bw_map:
        print("[INFO] Forward search yielded better results. Selecting as final optimal solution.")
        final_inputs, final_weights = fw_inputs, fw_weights
    else:
        print("[INFO] Backward search yielded better results. Selecting as final optimal solution.")
        final_inputs, final_weights = bw_inputs, bw_weights

    # Save the best combination to file
    with open("best_greedy_multipliers.txt", "w") as f:
        for i in range(11):
            f.write(f"{final_inputs[i]} {final_weights[i]}\n")
            
    print("[INFO] Final best combination saved to 'best_greedy_multipliers.txt'.")

if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    main()