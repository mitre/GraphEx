interface ServerResponse {
	success: boolean;
	errorText?: string;
	stringPayload?: string;
	jsonPayload?: any;
}

/**
 * Check for deep equality between two objects.
 *
 * @param obj1 The first object.
 * @param obj2 The second object
 *
 * @returns A boolean whether the two objects are equal.
 */
function isDeepEqual(obj1: { [key: string]: any }, obj2: { [key: string]: any }): boolean {
	// Check if the objects are strictly equal
	if (obj1 === obj2) {
		return true;
	}

	// Check if both objects are objects and not null
	if (typeof obj1 !== 'object' || obj1 === null || typeof obj2 !== 'object' || obj2 === null) {
		return false;
	}

	// Compare the number of properties in obj1 and obj2
	const keys1 = Object.keys(obj1);
	const keys2 = Object.keys(obj2);

	if (keys1.length !== keys2.length) {
		return false;
	}

	// Recursively compare properties and their values
	for (const key of keys1) {
		if (!keys2.includes(key) || !isDeepEqual(obj1[key], obj2[key])) {
			return false;
		}
	}

	return true;
}

export { isDeepEqual };
export type { ServerResponse };
