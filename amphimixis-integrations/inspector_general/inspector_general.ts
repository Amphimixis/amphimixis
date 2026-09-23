import fs from 'fs';
import type { Heading, Root, Table, TableCell, TableRow } from 'mdast';
import { gfmTableToMarkdown } from 'mdast-util-gfm-table';
import { toMarkdown } from 'mdast-util-to-markdown';
import { cwd } from 'process';
import remarkGfm from 'remark-gfm';
import remarkParse from 'remark-parse';
import { unified } from 'unified';

/** The type which children can be text or have children which can be text or children have children which ... */
type ParentOfTextChildren = Root | Table | TableRow | TableCell | Heading;

type Improvement = {
  parameter: string;
  measuredObject: string;
  baselineBuild: string;
  optimizedBuild: string;
  baselineValue: number;
  optimizedValue: number;
  improvementPcnt: number;
};

export default class InspectorGeneral {
  private static IMPROVEMENTS_HEADERS = [
    'Measured',
    'Baseline value',
    'Optimized value',
    'Improvement %'
  ];
  private static IMPROVEMENTS_HEADERS_NUM = InspectorGeneral.IMPROVEMENTS_HEADERS.length;

  private static CT_HEADERS = [
    'Symbol',
    '{First build name} %',
    '{Second build name} %',
    'Delta %'
  ];
  private static CT_HEADINGS_NUM = InspectorGeneral.CT_HEADERS.length;

  // Checking only a correctness of the improvements and cross-tables
  //  data in the report file
  static inspect(): [boolean, string[]] {
    let output: string[] = ['# Inspection results', ''];
    let isSuccessful: boolean = true;

    const crossTableContents: Table[] | undefined =
      InspectorGeneral.getCrossTableContentsFromAmixisFiles()
        ?.children.filter(
          (child) => child.type === 'table'
        );
    const improvements = InspectorGeneral.getImprovementsFromAmixisFile();
    const report = InspectorGeneral.getReportFromAmixisFile();

    let missingFilesOutput: string[] = ['## Missing required steps', ''];
    const baseLength = missingFilesOutput.length;
    if (crossTableContents === undefined) {
      missingFilesOutput.push(
        '- using `amphimixis-compare` tool to'
        + ' generate cross-table files'
      );
    }
    if (improvements === undefined) {
      missingFilesOutput.push(
        '- using `calculate-optimization-improvement`'
        + ' tool to get data about optimization improvements'
      );
    }
    if (report === undefined) {
      missingFilesOutput.push(
        '- FATAL: no report file found, please'
        + ' create a report'
      );
    }

    if (missingFilesOutput.length > baseLength) {
      missingFilesOutput.push(
        '- **IMPRORTANT**: mark these issues in the report file'
      );
      output = output.concat(missingFilesOutput);
      return [false, output];
    }

    let followingTableIsCrossTable: boolean = false;
    let followingTableIsImprovements: boolean = false;
    let baselineBuild: string = '';
    let optimizedBuild: string = '';
    for (const part of (report as Root).children) {
      if (part.type === 'heading') { // the heading is preceding the table
        const headingText = this.joinChildrenText(part);

        if (headingText.toLocaleLowerCase().search(/cross[- ]?table/) !== -1)
          followingTableIsCrossTable = true;

        if (headingText.toLocaleLowerCase().search(/improvement/) !== -1) {
          followingTableIsImprovements = true;

          const match = headingText.match(/Improvement of ([^\n ]+?) compared to ([^\n ]+?)/i);
          if (match !== null) {
            baselineBuild = match[1];
            optimizedBuild = match[2];
          }
        }
      }

      if (part.type === 'table') {
        if (followingTableIsCrossTable) {
          const [isCtInspectionSuccessful, ctOutput] =
            this.inspectReportCrossTable(part, crossTableContents as Table[])
          output = output.concat(ctOutput);
          isSuccessful &&= isCtInspectionSuccessful;
        }
        if (followingTableIsImprovements) {
          const [isImprvInspectionSuccessful, imprvsOutput] = InspectorGeneral.inspectReportImprovementsTable(
            part,
            improvements as Improvement[],
            baselineBuild,
            optimizedBuild,
          )
          output = output.concat(imprvsOutput);
          isSuccessful &&= isImprvInspectionSuccessful;
        }
        followingTableIsImprovements = false;
        followingTableIsCrossTable = false;
      }
    }
    return [isSuccessful, output];
  }

  private static joinChildrenText(root: ParentOfTextChildren, text: string = ''): string {
    if (!('children' in root))
      return text;

    for (const child of root.children) {
      if (child?.type === 'text')
        text += child?.value;
      if ('children' in child && child?.children)
        text +=
          InspectorGeneral.joinChildrenText(child as ParentOfTextChildren, text);
    }

    return text;
  }

  private static sortTableRowsByFirstColumn(table: Table): void {
    table.children.sort((a, b) => (
      InspectorGeneral.joinChildrenText(a.children[0])
        ?.localeCompare(
          InspectorGeneral.joinChildrenText(b.children[0])
        ) || 0
    ));
  }

  // Do not check the files, builds and events match to the cross-table
  private static inspectReportCrossTable(reportCTable: Table, cTables: Table[]): [boolean, string[]] {
    let output: string[] = ['', '## Cross-table inspection results', ''];
    let isSuccessful: boolean = true;
    if (
      // reportCTable: Table = { ..., children: TableRow[] }
      // TableRow { ..., children: TableCell[] }
      // TableCell { ..., children: <type kind of Text>[] }
      reportCTable?.children[0].children.length
      !== InspectorGeneral.CT_HEADERS.length // exactly equal
      || InspectorGeneral.joinChildrenText(reportCTable?.children[0]?.children[0])
      !== InspectorGeneral.CT_HEADERS[0]
      || !/.* %/.test(InspectorGeneral.joinChildrenText(
        reportCTable?.children[0]?.children[1]))
      || !/.* %/.test(InspectorGeneral.joinChildrenText(
        reportCTable?.children[0]?.children[2]))
      || InspectorGeneral.joinChildrenText(
        reportCTable?.children[0]?.children[3])
      !== InspectorGeneral.CT_HEADERS[3]
    ) {
      output.push(
        `- Cross - table must contain ONLY ${InspectorGeneral.CT_HEADINGS_NUM} columns with the`
        + ` headings in STRICT order: ${InspectorGeneral.CT_HEADERS.join(', ')}.`
      );
      isSuccessful = false;
    }

    InspectorGeneral.sortTableRowsByFirstColumn(reportCTable);
    lookUpTable: {
      for (const srcTable of cTables) {
        const cTable: Table = { ...srcTable, children: [...srcTable.children] };
        InspectorGeneral.sortTableRowsByFirstColumn(cTable);

        if (cTable.children.length !== reportCTable.children.length
          || cTable.children.length === 0)
          continue;

        tablesComparison: {
          for (let i: number = 0; i < reportCTable.children.length; ++i) {
            const reportRow = reportCTable.children[i];
            const cTableRow = cTable.children[i];
            if (
              reportRow.children.length
              !== cTableRow.children.length
            )
              break tablesComparison;

            for (
              let j: number = 0;
              j < reportRow.children.length;
              ++j
            ) {
              if (
                InspectorGeneral.joinChildrenText(cTable.children[i].children[j])
                !== InspectorGeneral.joinChildrenText(reportCTable.children[i].children[j])
              )
                break tablesComparison;
            }
          }
          break lookUpTable;

        } // tablesComparison

      }
      const mdReportCTable = toMarkdown(reportCTable, {
        extensions: [gfmTableToMarkdown()]
      });
      output.push(
        '- Table incorrect, read the "CT-<...>.md" files again'
        + ' and copy all tables from there without changes in the report:\n'
        + mdReportCTable
      );
      return [false, output];

    } // lookUpTable

    output.push('- All fine.')
    return [isSuccessful, output];
  }

  private static inspectReportImprovementsTable(
    reportImprovement: Table,
    improvements: Improvement[],
    baselineBuild: string,
    optimizedBuild: string,
  ): [boolean, string[]] {
    let output: string[] = ['', '## Improvements table inspection results', ''];
    let isSuccessful: boolean = true;
    if (
      // reportImprovement: Table = { ..., children: TableRow[] }
      // TableRow { ..., children: TableCell[] }
      // TableCell { ..., children: <type kind of Text>[] }
      reportImprovement?.children[0].children.length
      < InspectorGeneral.IMPROVEMENTS_HEADERS_NUM
      || InspectorGeneral.joinChildrenText(reportImprovement?.children[0]?.children[0])
      !== InspectorGeneral.IMPROVEMENTS_HEADERS[0]
      || InspectorGeneral.joinChildrenText(reportImprovement?.children[0]?.children[1])
      !== InspectorGeneral.IMPROVEMENTS_HEADERS[1]
      || InspectorGeneral.joinChildrenText(reportImprovement?.children[0]?.children[2])
      !== InspectorGeneral.IMPROVEMENTS_HEADERS[2]
      || InspectorGeneral.joinChildrenText(reportImprovement?.children[0]?.children[3])
      !== InspectorGeneral.IMPROVEMENTS_HEADERS[3]
    ) {
      output.push(
        `- Improvements table must contain ${InspectorGeneral.IMPROVEMENTS_HEADERS_NUM} columns at least with the`
        + ` headings in STRICT order: ${InspectorGeneral.IMPROVEMENTS_HEADERS.join(', ')}.`
      );
      output.push(
        '- If you want to add more columns, add them after the'
        + ` headings: ${InspectorGeneral.IMPROVEMENTS_HEADERS.join(', ')}.`
      )
      isSuccessful = false;
    }

    improvements = improvements.filter(
      (imprv) => (
        imprv.baselineBuild === baselineBuild
        && imprv.optimizedBuild === optimizedBuild
      )
    );

    searchingImprovementInFile: {
      for (const imprv of reportImprovement.children) {
        if (improvements.find(
          (imprvInFile) => (
            imprvInFile.measuredObject === InspectorGeneral.joinChildrenText(imprv.children[0])
            && imprvInFile.baselineValue
            === Number(InspectorGeneral.joinChildrenText(imprv.children[1]))
            && imprvInFile.optimizedValue
            === Number(InspectorGeneral.joinChildrenText(imprv.children[2]))
            && imprvInFile.improvementPcnt
            === Number(InspectorGeneral.joinChildrenText(imprv.children[3]))
          )
        ) !== undefined)
          break searchingImprovementInFile;
      }
      const mdReportImprovement = toMarkdown(reportImprovement, {
        extensions: [gfmTableToMarkdown()]
      });
      output.push(
        '- Improvements table contains incorrect data, read the'
        + ' "improvements.json" file again and copy all rows from there'
        + '  without changes in the report:\n'
        + mdReportImprovement
      );
      return [false, output];

    } // searchingImprovementInFile

    output.push('- All fine.')
    return [isSuccessful, output];
  }

  private static getCrossTableContentsFromAmixisFiles(): Root | undefined {
    const crossTablesDir = `${cwd()}/cross-tables`;
    let fileNames: string[];
    try {
      fileNames = fs.readdirSync(crossTablesDir)
        .filter(item => (item.startsWith('CT-') && item.endsWith('.md')));
    } catch {
      return undefined;
    }
    const fileContents =
      fileNames.map(
        (name) => fs.readFileSync(`${crossTablesDir}/${name}`, 'utf-8')
      ).join('\n');

    if (!fileContents)
      return undefined;

    let contents;
    try {
      contents = unified()
        .use(remarkParse)
        .use(remarkGfm)
        .parse(fileContents);
    } catch {
      return undefined;
    }

    return contents;
  }

  private static getImprovementsFromAmixisFile(): Improvement[] | undefined {
    const fileName: string | undefined = fs.readdirSync(cwd()).find(
      file => file === 'improvements.json'
    );
    if (!fileName)
      return undefined;
    const fileContent = fs.readFileSync(fileName as string, 'utf-8');

    let improvements: Improvement[];
    try {
      improvements = JSON.parse(fileContent);
    } catch {
      return undefined;
    }

    return improvements;
  }

  private static getReportFromAmixisFile(): Root | undefined {
    const fileName: string | undefined = fs.readdirSync(cwd()).find(
      file => /^amphimixis[-_].+?[-_]report\.md$/i.test(file)
    );
    if (!fileName)
      return undefined;
    const fileContent = fs.readFileSync(fileName as string, 'utf-8');

    let content;
    try {
      content = unified()
        .use(remarkParse)
        .use(remarkGfm)
        .parse(fileContent);
    } catch {
      return undefined;
    }

    return content;
  }
}
