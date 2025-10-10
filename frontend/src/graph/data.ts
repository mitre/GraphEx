/**
 * Metadata for a data type.
 */
interface DataTypeMetadata {
	/** The name of this data type. */
	name: string;

	/** The description of this data type. */
	description: string;

	/** The color to represent this data type. */
	color: string;
}

export type { DataTypeMetadata };
