export interface IRadar {
    readonly labels: string[];
    readonly values: number[];
}

export class Radar implements IRadar {
    constructor(
        public readonly labels: string[],
        public readonly values: number[]
    ) { }
}