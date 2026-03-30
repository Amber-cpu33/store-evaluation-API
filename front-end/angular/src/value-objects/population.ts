export interface ITotalPopulation {
    readonly neighborhood: number;
    readonly district: number;
}

export class TotalPopulation implements ITotalPopulation {
    constructor(
        public readonly neighborhood: number,
        public readonly district: number
    ) { }
}