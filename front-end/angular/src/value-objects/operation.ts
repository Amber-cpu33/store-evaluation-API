export interface IOperation {
    readonly score: number;
    readonly report: string;
}

export class Operation implements IOperation {
    constructor(
        public readonly score: number,
        public readonly report: string
    ) { }
}