"""Generate an editable PBIP report and TMSL semantic model (no credentials)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "powerbi"
BASE = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/"


def save(path, obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,indent=2)+"\n",encoding="utf-8")


def column(name, dtype="double"):
    result = {"name":name,"dataType":dtype,"sourceColumn":name,"summarizeBy":"none"}
    if dtype == "dateTime": result.update(formatString="yyyy-MM-dd",annotations=[{"name":"UnderlyingDateTimeDataType","value":"Date"}])
    if dtype == "double": result["formatString"] = "0.00"
    return result


def table(name, view, columns, measures=None):
    expr = ["let", "    Source = PostgreSQL.Database(Server, Database, [CreateNavigationProperties=false]),",
            f'    Data = Source{{[Schema="public", Item="{view}"]}}[Data]', "in", "    Data"]
    return {"name":name,"columns":[column(*c) if isinstance(c,tuple) else column(c) for c in columns],
            "partitions":[{"name":name,"mode":"import","source":{"type":"m","expression":expr}}],
            "measures":measures or []}


def measure(name, expression, fmt="0.00"):
    return {"name":name,"expression":expression,"formatString":fmt}


def field(table_name, name, kind="Column"):
    return {kind:{"Expression":{"SourceRef":{"Entity":table_name}},"Property":name}}


def projection(table_name,name,kind="Column",active=None):
    p = {"field":field(table_name,name,kind),"queryRef":f"{table_name}.{name}","nativeQueryRef":name}
    if active is not None: p["active"]=active
    return p


def literal(value):
    if isinstance(value,bool): value="true" if value else "false"
    elif isinstance(value,(float,int)): value=str(value)+"D"
    else: value="'"+value.replace("'","''")+"'"
    return {"expr":{"Literal":{"Value":value}}}


def visual(page, name, visual_type, title, x,y,w,h,roles=None,objects=None):
    v = {"visualType":visual_type,"drillFilterOtherVisuals":True,
         "visualContainerObjects":{
             "title":[{"properties":{"show":literal(True),"text":literal(title),"fontSize":literal(12)}}],
             "background":[{"properties":{"show":literal(True),"color":{"solid":{"color":literal("#FFFFFF")}},"transparency":literal(0)}}],
             "border":[{"properties":{"show":literal(False)}}]}}
    if roles: v["query"]={"queryState":{k:{"projections":p} for k,p in roles.items()}}
    if objects: v["objects"]=objects
    save(OUT/f"Banking.Report/definition/pages/{page}/visuals/{name}/visual.json",{
        "$schema":BASE+"visualContainer/2.1.0/schema.json","name":name,
        "position":{"x":x,"y":y,"z":0,"height":h,"width":w,"tabOrder":0},"visual":v})


def text(page,name,content,x,y,w,h,size=14):
    visual(page,name,"textbox","",x,y,w,h,objects={"general":[{"properties":{"paragraphs":[
        {"textRuns":[{"value":content,"textStyle":{"fontSize":f"{size}pt","fontFamily":"Segoe UI","color":"#17324D"}}]}]}}]})


def build():
    tables = []
    tables.append(table("Series","dim_series",[("series_id","string"),("title","string"),("units","string"),("frequency","string"),("category","string")]))
    tables.append(table("Monthly","vw_monthly_indicators",[("series_id","string"),("month","dateTime"),"value",("observation_count","int64")],
        [measure("Indicator value","AVERAGE(Monthly[value])"),
         measure("Fed funds","CALCULATE([Indicator value], REMOVEFILTERS(Series), Monthly[series_id] = \"FEDFUNDS\")"),
         measure("Unemployment","CALCULATE([Indicator value], REMOVEFILTERS(Series), Monthly[series_id] = \"UNRATE\")")]))
    tables.append(table("Yield Curve","vw_yield_curve",[("observation_date","dateTime"),"yield_10y","yield_2y","spread_bps",("is_inverted","boolean")],
        [measure("10Y yield","AVERAGE('Yield Curve'[yield_10y])"),measure("2Y yield","AVERAGE('Yield Curve'[yield_2y])"),
         measure("Spread (bps)","AVERAGE('Yield Curve'[spread_bps])","0.0"),
         measure("Inverted days","COUNTROWS(FILTER('Yield Curve', 'Yield Curve'[is_inverted] = TRUE()))","0")]))
    tables.append(table("Inflation","vw_cpi_yoy",[("month","dateTime"),"cpi_index","inflation_yoy_pct"],
        [measure("CPI inflation YoY","AVERAGE(Inflation[inflation_yoy_pct])")]))
    snapshot_measures = []
    for sid,label in [("FEDFUNDS","Latest fed funds"),("UNRATE","Latest unemployment"),("MORTGAGE30US","Latest mortgage"),("DRCCLACBS","Latest delinquency")]:
        snapshot_measures.append(measure(label,f'CALCULATE(MAX(Snapshot[value]), REMOVEFILTERS(Series), Snapshot[series_id] = "{sid}")', '0.00"%"'))
    snapshot_measures.append(measure("Stale series","COUNTROWS(FILTER(Snapshot, Snapshot[is_stale] = TRUE()))","0"))
    tables.append(table("Snapshot","vw_latest_snapshot",[("series_id","string"),("title","string"),("frequency","string"),("units","string"),("observation_date","dateTime"),"value",("age_days","int64"),("is_stale","boolean")],snapshot_measures))
    tables.append(table("Credit","vw_credit_quarterly",[("quarter_start","dateTime"),"delinquency_pct","fed_funds_pct","unemployment_pct"],
        [measure("Delinquency","AVERAGE(Credit[delinquency_pct])"),measure("Quarterly policy rate","AVERAGE(Credit[fed_funds_pct])")]))
    tables.append(table("Mortgage","vw_mortgage_spread",[("observation_date","dateTime"),"mortgage_pct","treasury_10y_pct","spread_pp"],
        [measure("Mortgage rate","AVERAGE(Mortgage[mortgage_pct])"),measure("Mortgage spread (pp)","AVERAGE(Mortgage[spread_pp])")]))
    tables.append(table("Pipeline","vw_pipeline_health",[("run_id","string"),("started_at","dateTime"),("run_status","string"),("series_id","string"),("series_status","string"),("rows_processed","int64"),("missing_values","int64"),("error_type","string")]))
    tables.append({"name":"Calendar","columns":[column("Date","dateTime"),column("Year","int64"),column("Quarter","string"),column("Month","dateTime")],
       "partitions":[{"name":"Calendar","mode":"import","source":{"type":"m","expression":[
          "let", "    Start = #date(2000,1,1),", "    Finish = #date(2035,12,31),",
          '    Days = Table.FromList(List.Dates(Start,Duration.Days(Finish-Start)+1,#duration(1,0,0,0)),Splitter.SplitByNothing(),{"Date"}),',
          '    Typed = Table.TransformColumnTypes(Days,{{"Date",type date}}),',
          '    Years = Table.AddColumn(Typed,"Year",each Date.Year([Date]),Int64.Type),',
          '    Quarters = Table.AddColumn(Years,"Quarter",each "Q" & Text.From(Date.QuarterOfYear([Date])),type text),',
          '    Months = Table.AddColumn(Quarters,"Month",each Date.StartOfMonth([Date]),type date)',"in","    Months"]}}],
       "hierarchies":[{"name":"Date hierarchy","levels":[{"name":"Year","ordinal":0,"column":"Year"},{"name":"Quarter","ordinal":1,"column":"Quarter"},{"name":"Month","ordinal":2,"column":"Month"}]}]})
    relationships = []
    for t,c in [("Monthly","month"),("Yield Curve","observation_date"),("Inflation","month"),("Credit","quarter_start"),("Mortgage","observation_date")]:
        relationships.append({"name":f"Calendar_{t}","fromTable":t,"fromColumn":c,"toTable":"Calendar","toColumn":"Date","crossFilteringBehavior":"oneDirection"})
    for t in ["Monthly","Snapshot"]:
        relationships.append({"name":f"Series_{t}","fromTable":t,"fromColumn":"series_id","toTable":"Series","toColumn":"series_id","crossFilteringBehavior":"oneDirection"})
    model = {"name":"Banking Economic Conditions","compatibilityLevel":1567,"model":{
        "culture":"en-US","defaultPowerBIDataSourceVersion":"powerBI_V3",
        "sourceQueryCulture":"en-US","tables":tables,"relationships":relationships,
        "expressions":[{"name":"Server","kind":"m","expression":'"localhost:5433" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]'},
                       {"name":"Database","kind":"m","expression":'"fred_pipeline" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]'}],
        "annotations":[{"name":"PBI_TimeIntelligenceEnabled","value":"0"}]}}
    save(OUT/"Banking.SemanticModel/model.bim",model)
    save(OUT/"Banking.SemanticModel/definition.pbism",{"$schema":"https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json","version":"1.0","settings":{}})
    save(OUT/"Banking.pbip",{"$schema":"https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json","version":"1.0","artifacts":[{"report":{"path":"Banking.Report"}}],"settings":{"enableAutoRecovery":True}})
    save(OUT/"Banking.Report/definition.pbir",{"$schema":"https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json","version":"4.0","datasetReference":{"byPath":{"path":"../Banking.SemanticModel"}}})
    save(OUT/"Banking.Report/definition/version.json",{"$schema":BASE+"versionMetadata/1.0.0/schema.json","version":"2.0.0"})
    theme = {"name":"Banking Navy","dataColors":["#147D92","#D49A32","#345995","#A3455B","#548C73"],"background":"#F3F6FA","foreground":"#17324D","tableAccent":"#147D92"}
    save(OUT/"Banking.Report/StaticResources/RegisteredResources/BankingNavy.json",theme)
    save(OUT/"Banking.Report/definition/report.json",{"$schema":BASE+"report/3.0.0/schema.json",
        "themeCollection":{"customTheme":{"name":"BankingNavy","reportVersionAtImport":{"visual":"2.1.0","page":"2.0.0","report":"3.0.0"},"type":"RegisteredResources"}},
        "resourcePackages":[{"name":"RegisteredResources","type":"RegisteredResources","items":[{"name":"BankingNavy","path":"BankingNavy.json","type":"CustomTheme"}]}]})
    pages = [("overview","01 Executive overview"),("rates","02 Rates & yield curve"),("inflation","03 Inflation & labor"),("credit","04 Credit & lending"),("quality","05 Data & pipeline health")]
    save(OUT/"Banking.Report/definition/pages/pages.json",{"$schema":BASE+"pagesMetadata/1.0.0/schema.json","pageOrder":[p for p,_ in pages],"activePageName":"overview"})
    for p,title in pages:
        save(OUT/f"Banking.Report/definition/pages/{p}/page.json",{"$schema":BASE+"page/2.0.0/schema.json","name":p,"displayName":title,"displayOption":"FitToPage","height":900,"width":1440})
        text(p,"heading",title.upper(),28,14,1384,55,25)
        text(p,"footer","Source: FRED / original data providers | Rates in percent; spreads in pp or bps | Observation dates are not release dates",28,854,1384,34,10)
        if p not in ["overview","quality"]:
            visual(p,"years","slicer","Filter years",28,82,280,95,{"Values":[projection("Calendar","Year")]})
    for i,label in enumerate(["Latest fed funds","Latest mortgage","Latest unemployment","Latest delinquency"]):
        visual("overview",f"kpi{i}","card",label,28+i*348,100,332,130,{"Values":[projection("Snapshot",label,"Measure")]})
    text("overview","context","U.S. BANKING CONDITIONS | Latest cards use each series' most recent available observation. Dates differ across series; check the table below.",28,68,1384,30,11)
    visual("overview","snapshot","tableEx","Latest available indicators and their observation periods",28,250,880,375,
           {"Values":[projection("Snapshot",x) for x in ["title","value","units","frequency","observation_date","is_stale"]]})
    text("overview","guide","READ THE SIGNALS\nBorrowing costs: policy and mortgage rates\nTerm structure: 10Y minus 2Y Treasury yield\nHousehold pressure: unemployment and delinquency\n\nThis report describes economic conditions, not an individual bank's profit, customers, or credit decisions.",932,250,480,375,17)
    text("overview","summary","EXECUTIVE REVIEW\nUse the detail pages to compare the latest values with history. Record three dated findings after loading real data. Do not interpret the synthetic demo as economic evidence.",28,648,1384,176,17)
    def line(p,n,title,t,axis,measures,x=28,y=198,w=1384,h=290,drill=False):
        cats = [projection(t,axis)]
        if drill: cats=[projection("Calendar","Year",active=True),projection("Calendar","Quarter",active=False),projection("Calendar","Month",active=False)]
        visual(p,n,"lineChart",title,x,y,w,h,{"Category":cats,"Y":[projection(t,m,"Measure") for m in measures]})
    line("rates","yields","Treasury yields (%) | drill from year to quarter to month","Yield Curve","observation_date",["10Y yield","2Y yield"],drill=True)
    line("rates","spread","10Y - 2Y spread (basis points): negative values indicate inversion","Yield Curve","observation_date",["Spread (bps)"],y=515)
    line("inflation","cpi","CPI inflation: percent change from the same month a year earlier","Inflation","month",["CPI inflation YoY"])
    line("inflation","labor","Policy rate and unemployment (%)","Monthly","month",["Fed funds","Unemployment"],y=515)
    line("credit","delinquency","Credit card delinquency and average policy rate (%) | quarterly observations","Credit","quarter_start",["Delinquency","Quarterly policy rate"])
    line("credit","mortgage","Mortgage rate less same-week Treasury mean (percentage points)","Mortgage","observation_date",["Mortgage spread (pp)"],y=515)
    visual("quality","freshness","tableEx","Freshness by observation period (publication lags differ)",28,100,1384,260,{"Values":[projection("Snapshot",x) for x in ["title","frequency","observation_date","age_days","is_stale"]]})
    visual("quality","runs","tableEx","Run history: partial and failed runs need attention",28,390,1384,400,{"Values":[projection("Pipeline",x) for x in ["started_at","run_status","series_id","series_status","rows_processed","missing_values","error_type"]]})
    print("Generated Power BI project with 5 pages, 9 tables and imported PostgreSQL views.")


if __name__ == "__main__":
    build()
