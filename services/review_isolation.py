"""Findings are atomic error domains; global bindings remain a hard boundary."""
from copy import deepcopy
from core.validation import ContractError
from services.validation_diagnostics import ErrorCollector,ValidationErrors


class PartialReviewError(ValidationErrors):
    def __init__(self,errors,partial_output,retained):
        super().__init__(errors)
        self.partial_output=partial_output
        self.diagnostic["retained_items"]=retained
        self.diagnostic["isolation_boundary"]="whole finding/check, including all local bases and component indexes"


class WireIsolation:
    def __init__(self,baseline,strict_parser,groups,mark_incomplete):
        self.baseline=baseline;self.strict_parser=strict_parser
        self.groups=groups;self.mark_incomplete=mark_incomplete
        self.accepted={};self.origins={};self.attempt=0

    def parse(self,value):
        self.attempt+=1;ec=ErrorCollector("review_isolation")
        root_ok=ec.fields(value,set(self.groups),set(),"$")
        for error in ec.errors:
            error.update(allowed_root_fields=sorted(self.groups),processing_options=["return_only_the_declared_root_arrays","omit_transport_type_and_wrappers"])
        root_ok=root_ok and not ec.errors
        for group,identity in self.groups.items():
            expected={item[identity] for item in self.baseline[group]}
            items=value.get(group) if root_ok else None
            if not ec.check(type(items) is list,"$."+group,"expected_array"):continue
            identities=[item.get(identity) if type(item) is dict else None for item in items]
            for i,item in enumerate(items):
                path=f"$.{group}[{i}]";key=identities[i]
                if not ec.check(type(key) in (str,int) and type(key) is not bool and key in expected,path+"."+identity,"known_frozen_item_required"):continue
                if not ec.check(identities.count(key)==1,path+"."+identity,"duplicate_identity_invalidates_all_duplicates"):continue
                probe=deepcopy(self.baseline)
                ordinal=next(j for j,b in enumerate(probe[group]) if b[identity]==key)
                probe[group][ordinal]=item
                try:self.strict_parser(probe)
                except ContractError as exc:
                    if not getattr(exc,"diagnostic",None):raise
                    for error in exc.diagnostic.get("errors",[exc.diagnostic]):
                        mapped=dict(error)
                        mapped["field_path"]=mapped["field_path"].replace(f"$.{group}[{ordinal}]",path,1)
                        ec.errors.append(mapped)
                else:
                    self.accepted[(group,key)]=deepcopy(item);self.origins[(group,key)]=self.attempt
            supplied={key for key in identities if type(key) in (str,int) and type(key) is not bool}
            ec.check(expected<=supplied,"$."+group,"each_frozen_item_must_be_supplied")
        merged=deepcopy(self.baseline);retained=[];missing=[]
        for group,identity in self.groups.items():
            for i,item in enumerate(merged[group]):
                key=(group,item[identity])
                if key in self.accepted:
                    merged[group][i]=self.accepted[key]
                    retained.append({"group":group,"id":item[identity],"response_attempt":self.origins[key]})
                else:missing.append(key)
        # Revalidate all projections and cross-field invariants after merging.
        output=self.strict_parser(merged)
        if ec.errors:
            output=self.mark_incomplete(output,missing,ec.errors)
            raise PartialReviewError(ec.errors,output,retained)
        return output
