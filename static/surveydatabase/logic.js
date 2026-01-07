let exercisesDB = null;
let swapHistory = {};

document.addEventListener("DOMContentLoaded", () => {
	console.log("logic.js: DOMContentLoaded");

	const form = document.getElementById("survey-form");
	if (form) {
		form.addEventListener("submit", handleFormSubmit);
		console.log("logic.js: submit listener attached");
	} else {
		console.warn("logic.js: Survey missing #survey-form");
	}

	const cancelBtn = document.getElementById("cancel-delete");
	const confirmBtn = document.getElementById("confirm-delete");

	if (cancelBtn) {
		cancelBtn.addEventListener("click", () => {
			document.getElementById("delete-modal").style.display = "none";
		});
	}

	if (confirmBtn) {
		confirmBtn.addEventListener("click", async () => {
			if (planToDelete) {
				const response = await fetch(`/delete_plan/${planToDelete}`, {
					method: "POST",
				});
				if (response.ok) {
					elementToRemove.closest(".plan-card").remove();
					document.getElementById("delete-modal").style.display = "none";
				}
			}
		});
	}
});

// --- Survey ---

async function handleFormSubmit(event) {
	event.preventDefault();
	try {
		const response = await fetch("/static/exercises.json");
		if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
		const data = await response.json();

		const userInput = getUserInput();
		const availableExercises = filterExercises(data, userInput);
		const workoutPlan = generateWorkoutPlan(availableExercises, userInput);

		const payload = {
			name: userInput.name,
			age: userInput.age,
			level: userInput.level,
			plan: workoutPlan,
		};

		const saveResponse = await fetch("/save_plan", {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify(payload),
		});

		if (saveResponse.ok) {
			window.location.href = "/plan";
		} else {
			alert("Log in, in order to save your plan!");
		}
	} catch (error) {
		console.error("Error:", error);
	}
}

const surveyForm = document.getElementById("survey-form");
if (surveyForm) surveyForm.addEventListener("submit", handleFormSubmit);

/**
 * @returns {object}
 */

function getUserInput() {
	const form = document.getElementById("survey-form");
	const selectedEquipment = Array.from(
		form.querySelectorAll('input[name="equipment"]:checked')
	).map((checkbox) => checkbox.value);
	return {
		name: form.querySelector("#name").value,
		age: parseInt(form.querySelector("#age").value, 10),
		trainingDays: parseInt(form.querySelector("#training-days").value, 10),
		level: form.querySelector('input[name="level"]:checked').value,
		equipment: selectedEquipment,
	};
}

/**
 * @param {Array} allExercises
 * @param {object} userInput
 * @returns {Array}
 */

function filterExercises(allExercises, userInput) {
	const levelHierarchy = {
		beginner: ["beginner"],
		intermediate: ["beginner", "intermediate"],
		expert: ["beginner", "intermediate", "expert"],
	};
	const allowedLevels = levelHierarchy[userInput.level];
	return allExercises.filter((exercise) => {
		if (exercise.category !== "strength") return false;
		if (!allowedLevels.includes(exercise.level)) return false;
		if (userInput.equipment.length === 0) {
			return exercise.equipment === "body only" || exercise.equipment === null;
		}
		return (
			userInput.equipment.includes(exercise.equipment) ||
			(userInput.equipment.includes("body only") && exercise.equipment === null)
		);
	});
}

/**
 * @param {Array} availableExercises
 * @param {object} userInput
 * @returns {object}
 */

function generateWorkoutPlan(availableExercises, userInput) {
	let exercisesPool = [...availableExercises];

	// Plans
	const splits = {
		1: {
			name: "Full Body Workout",
			days: [
				{
					name: "Full Body",
					muscles: [
						"klatka",
						"plecy",
						"nogi",
						"barki",
						"biceps",
						"triceps",
						"brzuch",
					],
				},
			],
		},
		2: {
			name: "Upper / Lower Split",
			days: [
				{
					name: "Upper Body",
					muscles: ["klatka", "plecy", "barki", "biceps", "triceps"],
				},
				{ name: "Lower Body", muscles: ["nogi", "pośladki", "brzuch"] },
			],
		},
		3: {
			name: "Push / Pull / Legs",
			days: [
				{ name: "Push", muscles: ["klatka", "barki", "triceps"] },
				{ name: "Pull", muscles: ["plecy", "biceps"] },
				{ name: "Legs and ABS", muscles: ["nogi", "brzuch"] },
			],
		},
		4: {
			name: "Upper / Lower / Upper / Lower",
			days: [
				{
					name: "Upper Body",
					muscles: ["klatka", "plecy", "barki", "biceps", "triceps"],
				},
				{ name: "Lower Body", muscles: ["nogi", "pośladki", "brzuch"] },
				{
					name: "Upper Body",
					muscles: ["klatka", "plecy", "barki", "biceps", "triceps"],
				},
				{ name: "Lower Body", muscles: ["nogi", "pośladki", "brzuch"] },
			],
		},
		5: {
			name: "Bro Split Classic",
			days: [
				{ name: "Chest", muscles: ["klatka"] },
				{ name: "Back", muscles: ["plecy"] },
				{ name: "Legs and ABS", muscles: ["nogi", "brzuch"] },
				{ name: "Shoulders", muscles: ["barki"] },
				{ name: "Arms and ABS", muscles: ["biceps", "triceps"] },
			],
		},
		6: {
			name: "Push / Pull / Legs (x2)",
			days: [
				{ name: "Push ", muscles: ["klatka", "barki", "triceps"] },
				{ name: "Pull ", muscles: ["plecy", "biceps"] },
				{ name: "Legs and ABS ", muscles: ["nogi", "brzuch"] },
				{ name: "Push ", muscles: ["klatka", "barki", "triceps"] },
				{ name: "Pull ", muscles: ["plecy", "biceps"] },
				{ name: "Legs and ABS", muscles: ["nogi", "brzuch"] },
			],
		},
	};

	// Grouping
	const muscleMap = {
		klatka: ["chest"],
		plecy: ["lats", "middle back", "traps", "lower back"],
		nogi: ["quadriceps", "hamstrings", "calves"],
		barki: ["shoulders"],
		biceps: ["biceps"],
		triceps: ["triceps"],
		brzuch: ["abdominals"],
		pośladki: ["glutes"],
	};

	const selectedSplit = splits[userInput.trainingDays] || splits[1];
	const finalPlan = {
		planName: selectedSplit.name,
		trainingDays: [],
	};

	selectedSplit.days.forEach((dayInfo) => {
		const exercisesForDay = [];
		let exercisesPerMuscle;

		if (userInput.trainingDays === 5) {
			exercisesPerMuscle = 3;
		} else {
			exercisesPerMuscle = 2;
		}

		dayInfo.muscles.forEach((muscleGroup) => {
			const targetMuscles = muscleMap[muscleGroup] || [];

			let matchingExercises = exercisesPool.filter((ex) =>
				ex.primaryMuscles.some((pm) => targetMuscles.includes(pm))
			);

			matchingExercises = shuffleArray(matchingExercises);

			const selected = matchingExercises.slice(0, exercisesPerMuscle);
			exercisesForDay.push(...selected);

			const selectedIds = selected.map((s) => s.id);
			exercisesPool = exercisesPool.filter(
				(ex) => !selectedIds.includes(ex.id)
			);
		});

		finalPlan.trainingDays.push({
			name: dayInfo.name,
			exercises: exercisesForDay,
		});
	});

	return finalPlan;
}

/**
 * @param {Array} array
 * @returns {Array}
 */

function shuffleArray(array) {
	for (let i = array.length - 1; i > 0; i--) {
		const j = Math.floor(Math.random() * (i + 1));
		[array[i], array[j]] = [array[j], array[i]];
	}
	return array;
}

let planToDelete = null;
let elementToRemove = null;

function deletePlan(planId, element) {
	planToDelete = planId;
	elementToRemove = element;
	document.getElementById("delete-modal").style.display = "flex";
}

document.getElementById("cancel-delete").addEventListener("click", () => {
	document.getElementById("delete-modal").style.display = "none";
});

document
	.getElementById("confirm-delete")
	.addEventListener("click", async () => {
		if (planToDelete) {
			const response = await fetch(`/delete_plan/${planToDelete}`, {
				method: "POST",
			});
			if (response.ok) {
				elementToRemove.closest(".plan-card").remove();
				document.getElementById("delete-modal").style.display = "none";
			}
		}
	});

async function swapExercise(planId, dayIdx, exIdx, muscle, userLevel) {
	if (!exercisesDB) {
		const resp = await fetch("/static/exercises.json");
		exercisesDB = await resp.json();
	}

	const containerId = `ex-${planId}-${dayIdx}-${exIdx}`;
	const container = document.getElementById(containerId);
	if (!container) return;

	const modal = document.getElementById(`modal-${planId}`);
	const currentExercisesInPlan = Array.from(modal.querySelectorAll("h4")).map(
		(h4) => h4.innerText
	);

	let filtered = exercisesDB.filter(
		(ex) =>
			ex.primaryMuscles.includes(muscle) &&
			ex.level === userLevel.toLowerCase() &&
			!currentExercisesInPlan.includes(ex.name)
	);

	if (filtered.length === 0) {
		alert(
			"No more unique exercises available for this muscle group in our database!"
		);
		return;
	}

	const newEx = filtered[Math.floor(Math.random() * filtered.length)];

	swapHistory[containerId] = container.innerHTML;

	container.querySelector("h4").innerText = newEx.name;
	const list = container.querySelector(".instruction-list");
	list.innerHTML = newEx.instructions
		.map((step) => `<li>${step}</li>`)
		.join("");

	const undoBtn = container.querySelector(".undo-icon");
	if (undoBtn) undoBtn.style.display = "inline-block";
}

function updateExerciseUI(planId, dayIdx, exIdx, ex) {
	const container = document.querySelector(`#ex-${planId}-${dayIdx}-${exIdx}`);
	container.querySelector("h4").innerText = ex.name;

	const list = container.querySelector("ol");
	list.innerHTML = "";
	ex.instructions.forEach((step) => {
		const li = document.createElement("li");
		li.innerText = step;
		list.appendChild(li);
	});
}

function undoSwap(planId, dayIdx, exIdx) {
	const containerId = `ex-${planId}-${dayIdx}-${exIdx}`;
	if (swapHistory[containerId]) {
		document.getElementById(containerId).innerHTML = swapHistory[containerId];
		delete swapHistory[containerId];
	}
}

async function handleReaction(postId, type) {
	try {
		const response = await fetch(`/react/${postId}/${type}`);

		if (!response.ok) {
			const errorData = await response.json();
			alert(errorData.message || "Login required!");
			return;
		}

		const data = await response.json();

		if (data.status === "success") {
			const reactionTypes = ["like", "heart", "muscle", "fire"];

			reactionTypes.forEach((rType) => {
				const countElement = document.getElementById(
					`count-${rType}-${postId}`
				);
				if (countElement) {
					countElement.innerText = data.counts[rType];
				}

				const btn = countElement.parentElement;
				if (rType === data.current_active) {
					btn.classList.add("active");
				} else {
					btn.classList.remove("active");
				}
			});
		}
	} catch (error) {
		console.error("Error updating reactions:", error);
	}
}
