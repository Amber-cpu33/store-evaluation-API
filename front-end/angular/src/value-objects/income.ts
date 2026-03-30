export interface IMedianIncome {
    readonly neighborhood: number;
    readonly district: number;
}

export class MedianIncome implements IMedianIncome {
    constructor(
        public readonly neighborhood: number,
        public readonly district: number
    ) { }
}