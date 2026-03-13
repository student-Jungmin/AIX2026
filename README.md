//=========================================================================
// UNIX
//=========================================================================
// Generate directories for the dataset
After decompressing the zip file, you can use the following commands:
	cd skeleton				// Direct to the code folder	
	make			        // Compile the code
	cd bin/dataset		    // Go to the bin/dataset/
	python make_list_cur.py	// Update the directories for test images

Run the code	
	cd ..				    						// Go to bin/
	sh script-unix-aix2024-test-all.sh				// Full-Precision: 	Do inference on all test images, and calculate mAP
	sh script-unix-aix2024-test-all-quantized.sh	// Quantization: 	Do inference on all test images, and calculate mAP 
	
	// You can test one image 
	sh script-unix-aix2024-test-one.sh				// Full-Precision: 	Do inference on ONE image
	sh script-unix-aix2024-test-one-quantized.sh	// Quantization: 	Do inference on ONE image

//=========================================================================
//Windows
//=========================================================================
Requirments: 
	+ Install Visual Studio as the Installation Guide
	+ Install Python

After decompressing the zip file, you can use the following commands:
- Go to skeleton
NOTE**: The code is tested with Visual Studion 2019. However, it should work well with other versions. 
	If there is a version conflict, 
		1. Remove yolo_cpu.sln
		2. Double click to yolo_cpu.vcxproj to make a new project with your VS version


NOTE**: Assume your code is located at C:\skeleton 
Open your Windows Terminal
	cd C:\skeleton\bin\dataset	// Go to the bin/dataset/
	python make_list_cur.py		// Update the directories for test images
	cd ..				    	// Go to bin/

Run the code	
	cd ..				    					// Go to bin/
	script-wins-aix2024-test-all.cmd			// Full-Precision: 	Do inference on all test images, and calculate mAP
	script-wins-aix2024-test-all-quantized.cmd	// Quantization: 	Do inference on all test images, and calculate mAP 
	
	// You can test on one image 
	script-wins-aix2024-test-one.cmd			// Full-Precision: 	Do inference on ONE image
	script-wins-aix2024-test-one-quantized.cmd	// Quantization: 	Do inference on ONE image


+++ Updated (26.03.13)

**NOTE**: Do not delete or move the directory skeleton/bin/log_feamap. The underlying execution engine requires this path for logging feature maps; removing it will result in a Segmentation Fault (core dumped) during model inference or evaluation.

[1] Environment Portability: Replaced hard-coded absolute paths with relative paths to ensure the codebase remains functional across different local and server environments without manual path configuration.

[2] Dynamic Parameter Loading: Transitioned from hard-coded constants to a file-based configuration system. Quantization multipliers are now dynamically loaded from /skeleton/bin/quant_multipliers.txt.

[3] Quantization Granularity: Shifted the quantization strategy from per-channel to per-layer quantization. This simplifies the hardware implementation while maintaining robust model performance.

[4] Hardware-Friendly Operations: Refined the quantization logic by replacing FP32 multiplications with bit-shifting operations. This significantly optimizes the model for deployment on hardware with limited floating-point support.

[5] Automated Optimization Search: Developed and integrated a bi-directional greedy search algorithm (/skeleton/bin/bidirectional_greedy.py). This tool automates the process of finding the optimal quantization multipliers for each layer to maximize mAP.